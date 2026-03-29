from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass(slots=True)
class ActionLogEntry:
    timestamp: str
    category: str
    title: str
    status: str
    detail: str


class ActionLogStore:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, *, category: str, title: str, status: str, detail: str) -> ActionLogEntry:
        entry = ActionLogEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            category=category,
            title=title,
            status=status,
            detail=detail,
        )
        with self.storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def recent(self, limit: int = 8) -> list[ActionLogEntry]:
        if not self.storage_path.exists():
            return []

        entries: list[ActionLogEntry] = []
        try:
            lines = self.storage_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        for line in reversed(lines):
            if len(entries) >= limit:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            entries.append(
                ActionLogEntry(
                    timestamp=str(payload.get("timestamp", "")),
                    category=str(payload.get("category", "")),
                    title=str(payload.get("title", "")),
                    status=str(payload.get("status", "")),
                    detail=str(payload.get("detail", "")),
                )
            )
        return entries
