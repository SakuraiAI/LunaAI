from importlib import import_module
from typing import Protocol, cast

from app.tools.internet import InternetTool


class SettingsLike(Protocol):
    default_workflow: str
    default_reasoning_box: str
    memory_review_interval: int
    lm_studio_model: str


def _default_settings() -> SettingsLike:
    settings_module = import_module("config.settings")
    settings_class = getattr(settings_module, "AppSettings")
    return cast(SettingsLike, settings_class())


class RuntimeStatusFormatter:
    def __init__(self, settings: SettingsLike | None = None, internet: InternetTool | None = None) -> None:
        self.settings = settings or _default_settings()
        self.internet = internet or InternetTool()

    def format(self) -> str:
        return (
            f"Model: {self.settings.lm_studio_model}\n"
            f"Workflow: {self.settings.default_workflow}\n"
            f"Internet: {'on' if self.internet.is_enabled() else 'off'} ({self.internet.mode()})\n"
            f"Reasoning default: {self.settings.default_reasoning_box}\n"
            f"Memory review interval: {self.settings.memory_review_interval}"
        )
