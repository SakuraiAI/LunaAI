from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.text_utils import repair_text


@dataclass(slots=True)
class AgentRunSnapshot:
    """Current visible run state for the Luna/Xeno agent loop.

    OpenAI's Agents SDK guidance separates orchestration, tool execution,
    approvals, state, and final results. This small local snapshot gives LunaAI
    the same kind of surface without forcing a new runtime dependency.
    """

    run_id: str
    created_at: str
    updated_at: str
    user_input: str
    input_source: str
    owner: str
    scope: str
    risk: str
    status: str
    vision_active: bool
    xeno_active: bool
    action_title: str = ""
    tool_name: str = ""
    requires_confirmation: bool = False
    final_message: str = ""
    notes: list[str] = field(default_factory=list)


class AgentRunStateStore:
    """Keeps the latest agent run inspectable by UI, chat, and debugging."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._current: AgentRunSnapshot | None = self._load()

    def start(
        self,
        *,
        user_input: str,
        input_source: str,
        owner: str,
        scope: str,
        risk: str,
        vision_active: bool,
        xeno_active: bool,
        status: str = "routed",
        note: str = "",
    ) -> AgentRunSnapshot:
        now = self._now()
        snapshot = AgentRunSnapshot(
            run_id=uuid4().hex[:12],
            created_at=now,
            updated_at=now,
            user_input=self._clean(user_input),
            input_source=str(input_source or "chat"),
            owner=str(owner or "Luna"),
            scope=str(scope or "conversation"),
            risk=str(risk or "none"),
            status=str(status or "routed"),
            vision_active=bool(vision_active),
            xeno_active=bool(xeno_active),
            notes=[self._clean(note)] if self._clean(note) else [],
        )
        self._current = snapshot
        self._save()
        return snapshot

    def update(self, **changes: Any) -> AgentRunSnapshot | None:
        if self._current is None:
            return None
        for key, value in changes.items():
            if key == "note":
                note = self._clean(value)
                if note:
                    self._current.notes.append(note)
                continue
            if key == "notes":
                if isinstance(value, list):
                    self._current.notes.extend(self._clean(item) for item in value if self._clean(item))
                continue
            if hasattr(self._current, key):
                setattr(self._current, key, value)
        self._current.updated_at = self._now()
        self._save()
        return self._current

    def current(self) -> AgentRunSnapshot | None:
        return self._current

    def to_payload(self) -> dict[str, Any]:
        if self._current is None:
            return {"active": False}
        payload = asdict(self._current)
        payload["active"] = self._current.status not in {"completed", "failed", "blocked", "cancelled"}
        return payload

    def format_current(self) -> str:
        if self._current is None:
            return "Agent run state: zatím tu není žádný běh."
        run = self._current
        lines = [
            "Agent run state:",
            f"- Run: {run.run_id}",
            f"- Status: {run.status}",
            f"- Owner: {run.owner}",
            f"- Source: {run.input_source}",
            f"- Scope: {run.scope}",
            f"- Risk: {run.risk}",
            f"- Vision: {'yes' if run.vision_active else 'no'}",
            f"- Xeno: {'yes' if run.xeno_active else 'no'}",
        ]
        if run.tool_name:
            lines.append(f"- Tool: {run.tool_name}")
        if run.action_title:
            lines.append(f"- Action: {run.action_title}")
        if run.requires_confirmation:
            lines.append("- Confirmation: waiting or required")
        if run.final_message:
            lines.append(f"- Result: {self._short(run.final_message)}")
        if run.notes:
            lines.append("- Notes: " + " | ".join(self._short(note, 100) for note in run.notes[-3:]))
        return "\n".join(lines)

    def _load(self) -> AgentRunSnapshot | None:
        if not self.storage_path.exists():
            return None
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            return AgentRunSnapshot(
                run_id=str(payload.get("run_id", "")),
                created_at=str(payload.get("created_at", "")),
                updated_at=str(payload.get("updated_at", "")),
                user_input=str(payload.get("user_input", "")),
                input_source=str(payload.get("input_source", "")),
                owner=str(payload.get("owner", "")),
                scope=str(payload.get("scope", "")),
                risk=str(payload.get("risk", "")),
                status=str(payload.get("status", "")),
                vision_active=bool(payload.get("vision_active", False)),
                xeno_active=bool(payload.get("xeno_active", False)),
                action_title=str(payload.get("action_title", "")),
                tool_name=str(payload.get("tool_name", "")),
                requires_confirmation=bool(payload.get("requires_confirmation", False)),
                final_message=str(payload.get("final_message", "")),
                notes=[str(item) for item in payload.get("notes", []) if str(item).strip()]
                if isinstance(payload.get("notes", []), list)
                else [],
            )
        except TypeError:
            return None

    def _save(self) -> None:
        if self._current is None:
            return
        try:
            self.storage_path.write_text(json.dumps(asdict(self._current), ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _clean(self, value: Any) -> str:
        return repair_text(str(value or "")).strip()

    def _short(self, value: str, limit: int = 140) -> str:
        text = " ".join(self._clean(value).split())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "..."
