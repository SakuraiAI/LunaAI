from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import AppSettings
from app.core.memory_coordinator import MemoryCoordinator
from app.core.prompt_builder import PromptBuilder
from app.core.runtime_status import RuntimeStatusFormatter
from app.memory.chat_memory import ChatMemory
from app.memory.long_memory import LongMemory
from app.models.local_model import LocalModel
from app.tools.internet import InternetTool
from app.workflow.manager import WorkflowManager


class LunaEngine:
    def __init__(self) -> None:
        self.settings = AppSettings()
        self.settings.ensure_directories()
        self.model = LocalModel(
            model_name=self.settings.lm_studio_model,
            base_url=self.settings.lm_studio_base_url,
            provider="lm_studio",
            api_token=self.settings.lm_studio_api_token,
        )
        self.memory = ChatMemory(Path(self.settings.memory_path))
        self.long_memory = LongMemory(Path(self.settings.long_memory_path))
        self.workflow = WorkflowManager()
        self.internet = InternetTool()

        try:
            timezone = ZoneInfo("Europe/Prague")
            timezone_name = "Europe/Prague"
        except ZoneInfoNotFoundError:
            timezone = None
            timezone_name = "local system time"

        self.prompt_builder = PromptBuilder(
            memory=self.memory,
            long_memory=self.long_memory,
            internet=self.internet,
            timezone=timezone,
            timezone_name=timezone_name,
        )
        self.memory_coordinator = MemoryCoordinator(
            chat_memory=self.memory,
            long_memory=self.long_memory,
            review_interval=self.settings.memory_review_interval,
        )
        self.runtime_status = RuntimeStatusFormatter(
            settings=self.settings,
            internet=self.internet,
        )

    def _handle_internet_command(self, user_input: str) -> str | None:
        command = user_input.strip().lower()

        if command == "/internet on":
            self.internet.set_enabled(True)
            return "Luna: Internet access enabled."

        if command == "/internet off":
            self.internet.set_enabled(False)
            return "Luna: Internet access disabled."

        if command == "/internet auto":
            self.internet.set_enabled(True)
            self.internet.set_mode("auto")
            return "Luna: Internet mode set to auto."

        if command == "/internet manual":
            self.internet.set_mode("manual")
            return "Luna: Internet mode set to manual."

        if command == "/internet status":
            return self.internet.status()

        if user_input.startswith("/search "):
            query = user_input[8:].strip()
            if not query:
                return "Luna: Please provide a search query."
            return self.internet.search(query)

        return None

    def _internet_context(self, user_input: str) -> str:
        if not self.internet.should_search(user_input):
            return ""

        result = self.internet.search(user_input)
        if result.startswith("Luna:"):
            return result[5:].strip()
        return result

    def get_runtime_status(self) -> str:
        return self.runtime_status.format()

    def get_memory_insights(self) -> str:
        return self.memory_coordinator.memory_insights()

    def build_prompt(
        self,
        user_input: str,
        mode: str,
        instruction: str = "",
        internet_context: str = "",
        selected_mode: str = "auto",
        reasoning_box: str = "black_box",
    ) -> list[dict[str, str]]:
        return self.prompt_builder.build(
            user_input=user_input,
            mode=mode,
            instruction=instruction,
            internet_context=internet_context,
            selected_mode=selected_mode,
            reasoning_box=reasoning_box,
        )

    def process_message(self, user_input: str) -> str:
        cleaned_input = user_input.strip()
        if not cleaned_input:
            return ""

        if cleaned_input.lower() == "exit":
            return "Luna: Goodbye."

        internet_result = self._handle_internet_command(cleaned_input)
        if internet_result is not None:
            return internet_result

        workflow_data = self.workflow.process(cleaned_input, self.memory.load_history())
        if workflow_data["system_message"]:
            return f"Luna: {workflow_data['system_message']}"

        selected_mode = workflow_data.get("selected_mode", workflow_data.get("mode", "auto"))
        self.memory_coordinator.remember_user_input(cleaned_input, selected_mode)

        internet_context = self._internet_context(workflow_data["user_input"])
        prompt = self.build_prompt(
            user_input=workflow_data["user_input"],
            mode=workflow_data["mode"],
            instruction=workflow_data.get("instruction", ""),
            internet_context=internet_context,
            selected_mode=workflow_data.get("selected_mode", "auto"),
            reasoning_box=workflow_data.get("reasoning_box", self.settings.default_reasoning_box),
        )

        response = self.model.generate(prompt)
        self.memory_coordinator.save_exchange(cleaned_input, response)
        return response

    def clear_history(self) -> None:
        self.memory_coordinator.clear_all()

    def run(self) -> None:
        print("LunaAI launched. Type 'exit' to quit.")
        print("Luna is ready. Just write naturally and it will choose the right style automatically.")

        while True:
            user_input = input("Ty: ").strip()
            if not user_input:
                continue

            response = self.process_message(user_input)
            if not response:
                continue

            print(response)
            if user_input.lower() == "exit":
                break
