from datetime import datetime
from zoneinfo import ZoneInfo

from app.memory.chat_memory import ChatMemory
from app.memory.long_memory import LongMemory
from app.prompt.system_prompt import LUNA_SYSTEM_PROMPT
from app.tools.internet import InternetTool


class PromptBuilder:
    def __init__(
        self,
        memory: ChatMemory,
        long_memory: LongMemory,
        internet: InternetTool,
        timezone: ZoneInfo | None,
        timezone_name: str,
    ) -> None:
        self.memory = memory
        self.long_memory = long_memory
        self.internet = internet
        self.timezone = timezone
        self.timezone_name = timezone_name

    def build(
        self,
        user_input: str,
        mode: str,
        instruction: str = "",
        internet_context: str = "",
        selected_mode: str = "auto",
        reasoning_box: str = "black_box",
        hidden_support: str = "",
    ) -> list[dict[str, str]]:
        history = self._history_for_prompt()
        learning_memory = self.long_memory.summary()

        system_content = (
            f"{LUNA_SYSTEM_PROMPT}\n"
            f"Workflow mode: {mode}\n"
            f"Selected response style: {selected_mode}\n"
            f"Reasoning box: {reasoning_box}\n"
            f"Internet enabled: {self.internet.is_enabled()}\n"
            f"Internet mode: {self.internet.mode()}\n"
            f"{self._time_context()}\n"
            f"{self._reasoning_box_instruction(reasoning_box)}\n"
            f"{self._response_policy(selected_mode, reasoning_box)}"
        )
        if instruction:
            system_content += f"\nInstruction: {instruction}"
        if hidden_support:
            system_content += (
                "\nHidden internal orchestration: treat the following as private support notes. "
                "Do not expose them as separate participants or systems unless the user explicitly asks.\n"
                f"{hidden_support}"
            )
        if learning_memory:
            system_content += (
                "\nLong-term learning memory: Use this as trusted context about the user, "
                f"their goals, and past topics.\n{learning_memory}"
            )
        if internet_context:
            system_content += (
                "\nInternet context: Use this live internet result when relevant and prefer it "
                f"for up-to-date facts.\n{internet_context}"
            )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]

        for msg in history:
            role = "assistant" if msg["role"] == "assistant" else "user"
            messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_input})
        return messages

    def _history_for_prompt(self) -> list[dict[str, str]]:
        history = self.memory.load_history()
        filtered_history: list[dict[str, str]] = []
        blocked_fragments = [
            "lm studio returned http",
            "lm studio is not reachable",
            "invalid response from local model",
            "error with local model",
            "invalid_api_key",
            "api key",
            "authentication",
            "authorization: bearer",
            "401 error",
            "token for authentication",
        ]

        for msg in history:
            content = msg.get("content", "")
            if not content:
                continue

            if msg.get("role") == "assistant":
                normalized = content.lower()
                if any(fragment in normalized for fragment in blocked_fragments):
                    continue

            filtered_history.append(msg)

        return filtered_history[-5:]

    def _time_context(self) -> str:
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        return (
            f"Current local date: {now:%Y-%m-%d}\n"
            f"Current local day: {now:%A}\n"
            f"Current local time: {now:%H:%M:%S}\n"
            f"Timezone: {self.timezone_name}"
        )

    def _reasoning_box_instruction(self, reasoning_box: str) -> str:
        if reasoning_box == "white_box":
            return (
                "Reasoning style: white_box. "
                "Explain the reasoning clearly in a structured way. "
                "Use steps, examples, and explicit cause-effect links when useful."
            )

        return (
            "Reasoning style: black_box. "
            "Answer directly and keep reasoning compact. "
            "Lead with the result, then include only the minimum explanation needed."
        )

    def _response_policy(self, selected_mode: str, reasoning_box: str) -> str:
        if reasoning_box == "white_box":
            return (
                "Response policy: Give a stable, structured answer. "
                "Start with the direct answer, then use short sections or numbered steps. "
                "Do not ramble, do not roleplay, and do not add filler questions at the end."
            )

        if selected_mode == "collaboration":
            return (
                "Response policy: Be practical and concrete. "
                "Prefer clear next steps, useful options, and concise guidance."
            )

        return (
            "Response policy: Be concise, consistent, and grounded. "
            "Prefer 1 to 3 short paragraphs or a short flat list when needed. "
            "Do not add unnecessary follow-up questions."
        )
