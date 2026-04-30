from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.core.text_utils import repair_text


@dataclass(slots=True)
class AgentTraceEntry:
    timestamp: str
    phase: str
    status: str
    source: str
    scope: str
    risk: str
    vision_active: bool
    xeno_active: bool
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentTraceStore:
    """Small AIQ-inspired workflow trace for Luna/Xeno agent turns.

    NVIDIA AIQ emphasizes composable workflows plus profiling and observability.
    This local store gives LunaAI a lightweight version of that idea without
    adding a new runtime dependency.
    """

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        phase: str,
        status: str,
        source: str = "unknown",
        scope: str = "unknown",
        risk: str = "none",
        vision_active: bool = False,
        xeno_active: bool = False,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AgentTraceEntry:
        entry = AgentTraceEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            phase=str(phase or "unknown"),
            status=str(status or "unknown"),
            source=str(source or "unknown"),
            scope=str(scope or "unknown"),
            risk=str(risk or "none"),
            vision_active=bool(vision_active),
            xeno_active=bool(xeno_active),
            detail=repair_text(str(detail or "")).strip(),
            metadata=dict(metadata or {}),
        )
        with self.storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def recent(self, limit: int = 8) -> list[AgentTraceEntry]:
        if not self.storage_path.exists():
            return []
        try:
            lines = self.storage_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        entries: list[AgentTraceEntry] = []
        for line in reversed(lines):
            if len(entries) >= limit:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            metadata = payload.get("metadata", {})
            entries.append(
                AgentTraceEntry(
                    timestamp=str(payload.get("timestamp", "")),
                    phase=str(payload.get("phase", "")),
                    status=str(payload.get("status", "")),
                    source=str(payload.get("source", "")),
                    scope=str(payload.get("scope", "")),
                    risk=str(payload.get("risk", "")),
                    vision_active=bool(payload.get("vision_active", False)),
                    xeno_active=bool(payload.get("xeno_active", False)),
                    detail=str(payload.get("detail", "")),
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
            )
        return entries

    def format_recent(self, limit: int = 8) -> str:
        entries = self.recent(limit)
        if not entries:
            return "Agent trace zatim nema zadne zaznamy."
        lines: list[str] = ["Agent trace:"]
        for entry in entries:
            vision = "vision" if entry.vision_active else "no-vision"
            xeno = "xeno" if entry.xeno_active else "no-xeno"
            lines.append(
                f"- [{entry.timestamp}] {entry.phase}/{entry.status} "
                f"source={entry.source} scope={entry.scope} risk={entry.risk} {vision} {xeno}"
            )
            if entry.detail:
                lines.append(f"  {entry.detail}")
        return "\n".join(lines)
