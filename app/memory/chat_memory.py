import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class ChatMemory:
    storage_path: Path | None = None
    history: list[dict[str, str]] = field(default_factory=list)
    sessions: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    titles: dict[str, str] = field(default_factory=dict)
    current_session_id: str = "default"

    def __post_init__(self) -> None:
        if self.storage_path is not None:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._read_storage()
        self._ensure_session(self.current_session_id)
        self.history = list(self.sessions[self.current_session_id])

    def _default_title(self, session_id: str) -> str:
        if session_id == "default":
            return "Main chat"
        return "New chat"

    def _ensure_session(self, session_id: str) -> None:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        if session_id not in self.titles:
            self.titles[session_id] = self._default_title(session_id)

    def _read_storage(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if isinstance(data, list):
            self.sessions = {"default": self._normalize_history(data)}
            self.titles = {"default": "Main chat"}
            self.current_session_id = "default"
            return

        if not isinstance(data, dict):
            return

        raw_sessions = data.get("sessions", {})
        if isinstance(raw_sessions, dict):
            for session_id, history in raw_sessions.items():
                if isinstance(session_id, str):
                    self.sessions[session_id] = self._normalize_history(history)

        raw_titles = data.get("titles", {})
        if isinstance(raw_titles, dict):
            for session_id, title in raw_titles.items():
                if isinstance(session_id, str) and isinstance(title, str):
                    self.titles[session_id] = title.strip() or self._default_title(session_id)

        current_session_id = data.get("current_session_id")
        if isinstance(current_session_id, str) and current_session_id:
            self.current_session_id = current_session_id

    def _normalize_history(self, raw_history: object) -> list[dict[str, str]]:
        if not isinstance(raw_history, list):
            return []

        history: list[dict[str, str]] = []
        for item in raw_history:
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
        payload = {
            "current_session_id": self.current_session_id,
            "titles": self.titles,
            "sessions": self.sessions,
        }
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _update_title_from_message(self, message: str) -> None:
        current_title = self.titles.get(self.current_session_id, self._default_title(self.current_session_id))
        default_title = self._default_title(self.current_session_id)
        user_message_count = sum(
            1 for entry in self.sessions.get(self.current_session_id, []) if entry.get("role") == "user"
        )
        if user_message_count != 1:
            return
        if current_title.strip() != default_title:
            return

        title = " ".join(message.strip().split())
        if not title:
            return
        if len(title) > 38:
            title = title[:35].rstrip() + "..."
        self.titles[self.current_session_id] = title

    def save_message(self, role: str, message: str) -> None:
        self._ensure_session(self.current_session_id)
        entry = {"role": role, "content": message}
        self.sessions[self.current_session_id].append(entry)
        self.history = list(self.sessions[self.current_session_id])
        if role == "user":
            self._update_title_from_message(message)
        self._persist()

    def load_history(self) -> list[dict[str, str]]:
        return list(self.history)

    def add_user_message(self, message: str) -> None:
        self.save_message("user", message)

    def add_assistant_message(self, message: str) -> None:
        self.save_message("assistant", message)

    def clear(self) -> None:
        self.sessions[self.current_session_id] = []
        self.history = []
        self.titles[self.current_session_id] = self._default_title(self.current_session_id)
        self._persist()

    def clear_history(self) -> None:
        self.clear()

    def list_sessions(self) -> list[dict[str, str]]:
        ordered_ids = list(self.sessions.keys())
        if self.current_session_id in ordered_ids:
            ordered_ids.remove(self.current_session_id)
            ordered_ids.insert(0, self.current_session_id)
        return [
            {
                "id": session_id,
                "title": self.titles.get(session_id, self._default_title(session_id)),
                "message_count": str(len(self.sessions.get(session_id, []))),
            }
            for session_id in ordered_ids
        ]

    def create_session(self, title: str = "New chat") -> str:
        session_id = uuid4().hex[:12]
        self.sessions[session_id] = []
        clean_title = title.strip() or "New chat"
        self.titles[session_id] = clean_title
        self.current_session_id = session_id
        self.history = []
        self._persist()
        return session_id

    def switch_session(self, session_id: str) -> list[dict[str, str]]:
        self._ensure_session(session_id)
        self.current_session_id = session_id
        self.history = list(self.sessions[session_id])
        self._persist()
        return self.load_history()

    def delete_session(self, session_id: str) -> str:
        if session_id not in self.sessions:
            return self.current_session_id

        del self.sessions[session_id]
        self.titles.pop(session_id, None)

        if not self.sessions:
            self.sessions["default"] = []
            self.titles["default"] = "Main chat"
            self.current_session_id = "default"
        elif self.current_session_id == session_id:
            self.current_session_id = next(iter(self.sessions.keys()))

        self._ensure_session(self.current_session_id)
        self.history = list(self.sessions[self.current_session_id])
        self._persist()
        return self.current_session_id

    def rename_session(self, session_id: str, title: str) -> str:
        self._ensure_session(session_id)
        clean_title = " ".join(title.strip().split())
        if not clean_title:
            clean_title = self._default_title(session_id)
        if len(clean_title) > 60:
            clean_title = clean_title[:57].rstrip() + "..."
        self.titles[session_id] = clean_title
        self._persist()
        return clean_title

    def get_current_session_id(self) -> str:
        return self.current_session_id

    def get_current_session_title(self) -> str:
        return self.titles.get(self.current_session_id, self._default_title(self.current_session_id))

