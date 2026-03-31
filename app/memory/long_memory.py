import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.text_utils import dedupe_preserve_order, repair_text


@dataclass(slots=True)
class LongMemory:
    storage_path: Path | None = None
    knowledge: dict[str, list[str]] = field(default_factory=dict)
    reviewed_messages: int = 0

    def __post_init__(self) -> None:
        self.knowledge = {
            "profile": [],
            "preferences": [],
            "goals": [],
            "facts": [],
            "topics": [],
        }

        if self.storage_path is not None:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        if self.storage_path is None or not self.storage_path.exists():
            return

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(payload, dict):
            return

        knowledge = payload.get("knowledge", payload)
        if isinstance(knowledge, dict):
            for key in self.knowledge:
                values = knowledge.get(key, [])
                if isinstance(values, list):
                    cleaned = [repair_text(value) for value in values if isinstance(value, str) and value.strip()]
                    self.knowledge[key] = dedupe_preserve_order(cleaned[-24:], normalizer=lambda item: " ".join(item.lower().split()), limit=12)

        reviewed_messages = payload.get("reviewed_messages", 0)
        if isinstance(reviewed_messages, int) and reviewed_messages >= 0:
            self.reviewed_messages = reviewed_messages

    def _persist(self) -> None:
        if self.storage_path is None:
            return

        payload = {
            "knowledge": self.knowledge,
            "reviewed_messages": self.reviewed_messages,
        }
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, category: str, value: str) -> None:
        normalized = repair_text(value).strip()
        if not normalized or category not in self.knowledge:
            return

        items = self.knowledge[category]
        if normalized in items:
            return

        items.append(normalized)
        self.knowledge[category] = items[-12:]
        self._persist()

    def remember_from_user_input(self, user_input: str) -> None:
        text = repair_text(user_input).strip()
        lowered = text.lower()
        if not text:
            return

        profile_markers = ["my name is ", "i am ", "jmenuji se "]
        preference_markers = ["i like ", "i love ", "mam rad ", "muj oblibeny "]
        goal_markers = ["i want to learn ", "i want to improve ", "chci se naucit ", "chci zlepsit "]
        fact_markers = ["i work on ", "i am building ", "pracuji na ", "delam na "]

        self._capture_after_marker(text, lowered, profile_markers, "profile")
        self._capture_after_marker(text, lowered, preference_markers, "preferences")
        self._capture_after_marker(text, lowered, goal_markers, "goals")
        self._capture_after_marker(text, lowered, fact_markers, "facts")

    def remember_lesson(self, user_input: str, selected_mode: str) -> None:
        if selected_mode not in {"learning", "auto"}:
            return

        topic = self._extract_topic(user_input)
        if topic:
            self.add("topics", topic)

    def review_history(self, history: list[dict[str, str]]) -> bool:
        if self.reviewed_messages >= len(history):
            return False

        new_entries = history[self.reviewed_messages :]
        added_anything = False

        for item in new_entries:
            if item.get("role") != "user":
                continue

            before = self.summary()
            content = item.get("content", "")
            self.remember_from_user_input(content)
            self.remember_lesson(content, "auto")
            after = self.summary()
            if after != before:
                added_anything = True

        self.reviewed_messages = len(history)
        self._persist()
        return added_anything

    def _capture_after_marker(
        self,
        original_text: str,
        lowered_text: str,
        markers: list[str],
        category: str,
    ) -> None:
        for marker in markers:
            position = lowered_text.find(marker)
            if position == -1:
                continue

            value = original_text[position + len(marker) :].strip(" .,!?")
            if value:
                self.add(category, value)
            return

    def _extract_topic(self, user_input: str) -> str:
        lowered = user_input.lower().strip()
        prefixes = [
            "explain ",
            "teach me ",
            "what is ",
            "how does ",
            "why does ",
            "vysvetli ",
            "co je ",
            "jak funguje ",
            "proc ",
        ]

        for prefix in prefixes:
            if lowered.startswith(prefix):
                topic = user_input[len(prefix) :].strip(" .!?")
                return topic[:120]

        if len(user_input.split()) <= 10:
            return user_input.strip(" .!?")[:120]

        return ""

    def summary(self) -> str:
        parts: list[str] = []
        labels = {
            "profile": "User profile",
            "preferences": "User preferences",
            "goals": "Learning goals",
            "facts": "Current projects or facts",
            "topics": "Previously discussed topics",
        }

        for key, label in labels.items():
            values = self.knowledge.get(key, [])
            if values:
                parts.append(f"{label}: " + " | ".join(values[-4:]))

        return "\n".join(parts)

    def clear(self) -> None:
        for key in self.knowledge:
            self.knowledge[key] = []
        self.reviewed_messages = 0
        self._persist()
