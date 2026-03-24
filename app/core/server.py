from importlib import import_module
from typing import Protocol, cast


class SettingsLike(Protocol):
    app_name: str
    host: str
    port: int


def _default_settings() -> SettingsLike:
    settings_module = import_module("config.settings")
    settings_class = getattr(settings_module, "AppSettings")
    return cast(SettingsLike, settings_class())


class LunaServer:
    def __init__(self, settings: SettingsLike | None = None) -> None:
        self.settings = settings or _default_settings()

    def status(self) -> dict[str, str | int]:
        return {
            "app": self.settings.app_name,
            "host": self.settings.host,
            "port": self.settings.port,
        }
