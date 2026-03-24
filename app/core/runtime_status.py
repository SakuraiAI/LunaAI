from config.settings import AppSettings
from app.tools.internet import InternetTool


class RuntimeStatusFormatter:
    def __init__(self, settings: AppSettings, internet: InternetTool) -> None:
        self.settings = settings
        self.internet = internet

    def format(self) -> str:
        return (
            f"Model: {self.settings.lm_studio_model}\n"
            f"Workflow: {self.settings.default_workflow}\n"
            f"Internet: {'on' if self.internet.is_enabled() else 'off'} ({self.internet.mode()})\n"
            f"Reasoning default: {self.settings.default_reasoning_box}\n"
            f"Memory review interval: {self.settings.memory_review_interval}"
        )
