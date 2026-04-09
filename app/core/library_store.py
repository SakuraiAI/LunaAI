from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from uuid import uuid4


TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".log",
    ".ini",
    ".toml",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
}


@dataclass(slots=True)
class LibraryEntry:
    id: str
    title: str
    kind: str
    source: str
    content: str = ""
    tags: list[str] = field(default_factory=list)


class LibraryStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[LibraryEntry] = []
        self.load()

    def load(self) -> list[LibraryEntry]:
        if not self.storage_path.exists():
            return self.entries
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self.entries
        if not isinstance(payload, dict):
            return self.entries
        raw_entries = payload.get("entries", [])
        if not isinstance(raw_entries, list):
            return self.entries
        self.entries = []
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            entry_id_raw = item.get("id")
            title_raw = item.get("title")
            kind_raw = item.get("kind")
            source_raw = item.get("source")
            content_raw = item.get("content", "")
            tags_raw = item.get("tags", [])
            if not isinstance(entry_id_raw, str):
                continue
            if not isinstance(title_raw, str):
                continue
            if not isinstance(kind_raw, str):
                continue
            if not isinstance(source_raw, str):
                continue
            entry_id = entry_id_raw
            title = title_raw.strip() or "Library item"
            kind = kind_raw.strip() or "note"
            source = source_raw.strip()
            content = content_raw.strip() if isinstance(content_raw, str) else ""
            clean_tags = [tag.strip() for tag in tags_raw if isinstance(tag, str) and tag.strip()]
            self.entries.append(
                LibraryEntry(
                    id=entry_id,
                    title=title,
                    kind=kind,
                    source=source,
                    content=content,
                    tags=clean_tags[:8],
                )
            )
        return self.entries

    def save(self) -> None:
        payload = {"entries": [asdict(entry) for entry in self.entries]}
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_entries(self) -> list[dict[str, str]]:
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "kind": entry.kind,
                "source": entry.source,
                "preview": self._preview(entry.content),
            }
            for entry in self.entries
        ]

    def remove_entry(self, entry_id: str) -> bool:
        before = len(self.entries)
        self.entries = [entry for entry in self.entries if entry.id != entry_id]
        changed = len(self.entries) != before
        if changed:
            self.save()
        return changed

    def add_note(self, title: str, content: str, tags: list[str] | None = None) -> LibraryEntry:
        return self._upsert_entry(
            title=title.strip() or "Library note",
            kind="note",
            source=f"note:{uuid4().hex[:12]}",
            content=content.strip(),
            tags=tags or [],
        )

    def add_link(self, title: str, url: str, tags: list[str] | None = None) -> LibraryEntry:
        return self._upsert_entry(
            title=title.strip() or url.strip(),
            kind="link",
            source=url.strip(),
            content=url.strip(),
            tags=tags or [],
        )

    def add_file(self, file_path: str, tags: list[str] | None = None) -> LibraryEntry | None:
        path = Path(file_path)
        if not path.exists():
            return None
        excerpt = self._read_excerpt(path)
        return self._upsert_entry(
            title=path.name,
            kind="file",
            source=str(path),
            content=excerpt,
            tags=tags or [],
        )

    def sync_folder(self, folder_path: str) -> int:
        root = Path(folder_path)
        if not root.exists() or not root.is_dir():
            return 0
        added = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            existing = self._find_by_source(str(path))
            excerpt = self._read_excerpt(path)
            if existing is None:
                self.entries.insert(
                    0,
                    LibraryEntry(
                        id=uuid4().hex[:12],
                        title=path.name,
                        kind="cloud_file",
                        source=str(path),
                        content=excerpt,
                        tags=["cloud"],
                    ),
                )
                added += 1
                continue
            if existing.content != excerpt:
                existing.content = excerpt
                added += 1
        if added:
            self.entries = self.entries[:200]
            self.save()
        return added

    def relevant_context(self, query: str, limit: int = 3) -> str:
        tokens = [token for token in query.lower().split() if len(token) > 2]
        if not tokens:
            return ""
        scored: list[tuple[int, LibraryEntry]] = []
        for entry in self.entries:
            haystack = " ".join([entry.title, entry.kind, entry.source, entry.content, " ".join(entry.tags)]).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, entry))
        if not scored:
            return ""
        scored.sort(key=lambda item: item[0], reverse=True)
        lines: list[str] = []
        for _, entry in scored[:limit]:
            lines.append(f"{entry.title} ({entry.kind})")
            if entry.source:
                lines.append(f"Source: {entry.source}")
            if entry.content:
                lines.append(entry.content[:600])
        return "\n\n".join(lines)

    def _upsert_entry(self, *, title: str, kind: str, source: str, content: str, tags: list[str]) -> LibraryEntry:
        existing = self._find_by_source(source)
        clean_tags = [tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()][:8]
        if existing is not None:
            existing.title = title
            existing.kind = kind
            existing.content = content[:4000]
            existing.tags = clean_tags
            self.save()
            return existing
        entry = LibraryEntry(
            id=uuid4().hex[:12],
            title=title,
            kind=kind,
            source=source,
            content=content[:4000],
            tags=clean_tags,
        )
        self.entries.insert(0, entry)
        self.entries = self.entries[:200]
        self.save()
        return entry

    def _find_by_source(self, source: str) -> LibraryEntry | None:
        for entry in self.entries:
            if entry.source == source:
                return entry
        return None

    def _read_excerpt(self, path: Path) -> str:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:4000].strip()
        except OSError:
            return ""

    def _preview(self, content: str) -> str:
        preview = " ".join(content.split())
        return preview[:120] + ("..." if len(preview) > 120 else "")


