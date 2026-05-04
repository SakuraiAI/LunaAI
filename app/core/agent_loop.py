from __future__ import annotations

from dataclasses import dataclass, field

from app.core.text_utils import repair_text


@dataclass(slots=True)
class AgentLoopStep:
    index: int
    title: str
    status: str
    ok: bool
    message: str
    detail: str = ""
    repair: bool = False


@dataclass(slots=True)
class AgentLoopResult:
    """Compact execution report for the autonomous agent loop."""

    ok: bool = False
    status: str = "running"
    executed: int = 0
    repaired: int = 0
    failed: int = 0
    stopped_reason: str = ""
    messages: list[str] = field(default_factory=list)
    steps: list[AgentLoopStep] = field(default_factory=list)

    def add_step(self, step: AgentLoopStep) -> None:
        self.steps.append(step)
        message = repair_text(step.message).strip()
        if message:
            self.messages.append(message)
        if step.repair and step.ok:
            self.repaired += 1
        elif not step.repair and step.ok:
            self.executed += 1
        elif not step.ok:
            self.failed += 1

    def finish(self, *, ok: bool, status: str, stopped_reason: str) -> None:
        self.ok = ok
        self.status = status
        self.stopped_reason = stopped_reason

    def summary(self) -> str:
        status_text = {
            "completed": "Agent loop dokoncen.",
            "in_progress": "Agent loop bezi a ceka na dalsi stav.",
            "failed": "Agent loop se zastavil na chybe.",
            "blocked": "Agent loop byl zastaven bezpecnostni politikou.",
        }.get(self.status, f"Agent loop: {self.status}.")
        counts = f"Kroky: {self.executed}, opravy: {self.repaired}, chyby: {self.failed}."
        reason = f" Duvod zastaveni: {self.stopped_reason}" if self.stopped_reason else ""
        message_parts = [message for message in self.messages if message]
        if message_parts:
            return f"{status_text} {counts}{reason}\n\n" + "\n".join(f"- {message}" for message in message_parts[:8])
        return f"{status_text} {counts}{reason}".strip()
