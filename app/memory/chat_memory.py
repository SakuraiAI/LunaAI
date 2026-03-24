import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ChatMemory:
    storage_path: Path | None = None
    history: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.storage_path is not None:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.history = self._read_history()

    def _read_history(self) -> list[dict[str, str]]:
        if self.storage_path is None or not self.storage_path.exists():
            return []

        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(data, list):
            return []

        history: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history.append({"role": role, "content": content})
        return history

    def _persist(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.write_text(
            json.dumps(self.history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_message(self, role: str, message: str) -> None:
        self.history.append({"role": role, "content": message})
        self._persist()

    def load_history(self) -> list[dict[str, str]]:
        return list(self.history)

    def add_user_message(self, message: str) -> None:
        self.save_message("user", message)

    def add_assistant_message(self, message: str) -> None:
        self.save_message("assistant", message)

    def clear(self) -> None:
        self.history.clear()
        self._persist()
