from typing import Protocol

from app.memory.chat_memory import ChatMemory
from app.memory.long_memory import LongMemory


class ChatMemoryLike(Protocol):
    def save_message(self, role: str, message: str) -> None:
        ...

    def load_history(self) -> list[dict[str, str]]:
        ...

    def clear(self) -> None:
        ...


class MemoryCoordinator:
    def __init__(
        self,
        chat_memory: ChatMemoryLike,
        long_memory: LongMemory,
        review_interval: int,
    ) -> None:
        self.chat_memory = chat_memory
        self.long_memory = long_memory
        self.review_interval = review_interval
        self.message_counter = 0

    def remember_user_input(self, user_input: str, selected_mode: str) -> None:
        self.long_memory.remember_from_user_input(user_input)
        self.long_memory.remember_lesson(user_input, selected_mode)

    def save_exchange(self, user_input: str, response: str) -> None:
        self.chat_memory.save_message("user", user_input)
        self.chat_memory.save_message("assistant", response)
        self.message_counter += 1
        self.review_if_needed()

    def review_if_needed(self) -> None:
        if self.message_counter < self.review_interval:
            return

        self.long_memory.review_history(self.chat_memory.load_history())
        self.message_counter = 0

    def memory_insights(self) -> str:
        summary = self.long_memory.summary()
        if summary:
            return summary
        return "No long-term insights yet. Luna will start building them from your conversation."

    def clear_all(self) -> None:
        self.chat_memory.clear()
        self.long_memory.clear()
        self.message_counter = 0
