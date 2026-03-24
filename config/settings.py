from dataclasses import dataclass
from pathlib import Path


APP_NAME = "LunaAI"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
MODEL_TYPE = "local"
MEMORY_PATH = "data/chats/chat_history.json"
LONG_MEMORY_PATH = "data/chats/long_memory.json"
DEFAULT_WORKFLOW = "auto"
DEFAULT_REASONING_BOX = "black_box"
MEMORY_REVIEW_INTERVAL = 6

LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/api/v1/chat"
LM_STUDIO_MODEL = "google/gemma-3-4b"
LM_STUDIO_API_TOKEN = "sk-lm-1DNoipXs:BMFIcisE26fTdIcyKter"

INTERNET_ENABLED = True
INTERNET_MODE = "auto"


@dataclass(slots=True)
class AppSettings:
    app_name: str = APP_NAME
    host: str = APP_HOST
    port: int = APP_PORT
    model_type: str = MODEL_TYPE
    memory_path: str = MEMORY_PATH
    long_memory_path: str = LONG_MEMORY_PATH
    default_workflow: str = DEFAULT_WORKFLOW
    default_reasoning_box: str = DEFAULT_REASONING_BOX
    memory_review_interval: int = MEMORY_REVIEW_INTERVAL
    lm_studio_base_url: str = LM_STUDIO_BASE_URL
    lm_studio_model: str = LM_STUDIO_MODEL
    lm_studio_api_token: str = LM_STUDIO_API_TOKEN
    internet_enabled: bool = INTERNET_ENABLED
    internet_mode: str = INTERNET_MODE

    def ensure_directories(self) -> None:
        Path(self.memory_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.long_memory_path).parent.mkdir(parents=True, exist_ok=True)


__all__ = [
    "AppSettings",
    "APP_NAME",
    "APP_HOST",
    "APP_PORT",
    "MODEL_TYPE",
    "MEMORY_PATH",
    "LONG_MEMORY_PATH",
    "DEFAULT_WORKFLOW",
    "DEFAULT_REASONING_BOX",
    "MEMORY_REVIEW_INTERVAL",
    "LM_STUDIO_BASE_URL",
    "LM_STUDIO_MODEL",
    "LM_STUDIO_API_TOKEN",
    "INTERNET_ENABLED",
    "INTERNET_MODE",
]
