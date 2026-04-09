from dataclasses import dataclass
from pathlib import Path


APP_NAME = "LunaAI"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
MODEL_TYPE = "local"
MEMORY_PATH = "data/chats/chat_history.json"
LONG_MEMORY_PATH = "data/chats/long_memory.json"
USER_SETTINGS_PATH = "data/settings/user_settings.json"
PROJECTS_PATH = "data/projects/projects.json"
LIBRARY_PATH = "data/library/library.json"
DEFAULT_WORKFLOW = "auto"
DEFAULT_REASONING_BOX = "black_box"
MEMORY_REVIEW_INTERVAL = 6

LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/api/v1/chat"
LM_STUDIO_MODEL = "google/gemma-3-4b"
LM_STUDIO_API_TOKEN = "sk-lm-hNXsABqF:IJ0GSqx6rcQ7vZ1HeMN6"
LM_STUDIO_TIMEOUT_SECONDS = 180

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
NVIDIA_API_TOKEN = "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"
NVIDIA_TIMEOUT_SECONDS = 180
NVIDIA_REASONING_BUDGET = 16384
NVIDIA_ENABLE_THINKING = True

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
    user_settings_path: str = USER_SETTINGS_PATH
    projects_path: str = PROJECTS_PATH
    library_path: str = LIBRARY_PATH
    default_workflow: str = DEFAULT_WORKFLOW
    default_reasoning_box: str = DEFAULT_REASONING_BOX
    memory_review_interval: int = MEMORY_REVIEW_INTERVAL
    lm_studio_base_url: str = LM_STUDIO_BASE_URL
    lm_studio_model: str = LM_STUDIO_MODEL
    lm_studio_api_token: str = LM_STUDIO_API_TOKEN
    lm_studio_timeout_seconds: int = LM_STUDIO_TIMEOUT_SECONDS
    nvidia_base_url: str = NVIDIA_BASE_URL
    nvidia_model: str = NVIDIA_MODEL
    nvidia_api_token: str = NVIDIA_API_TOKEN
    nvidia_timeout_seconds: int = NVIDIA_TIMEOUT_SECONDS
    nvidia_reasoning_budget: int = NVIDIA_REASONING_BUDGET
    nvidia_enable_thinking: bool = NVIDIA_ENABLE_THINKING
    internet_enabled: bool = INTERNET_ENABLED
    internet_mode: str = INTERNET_MODE

    def ensure_directories(self) -> None:
        Path(self.memory_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.long_memory_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.user_settings_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.projects_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.library_path).parent.mkdir(parents=True, exist_ok=True)


__all__ = [
    "AppSettings",
    "APP_NAME",
    "APP_HOST",
    "APP_PORT",
    "MODEL_TYPE",
    "MEMORY_PATH",
    "LONG_MEMORY_PATH",
    "USER_SETTINGS_PATH",
    "PROJECTS_PATH",
    "LIBRARY_PATH",
    "DEFAULT_WORKFLOW",
    "DEFAULT_REASONING_BOX",
    "MEMORY_REVIEW_INTERVAL",
    "LM_STUDIO_BASE_URL",
    "LM_STUDIO_MODEL",
    "LM_STUDIO_API_TOKEN",
    "LM_STUDIO_TIMEOUT_SECONDS",
    "NVIDIA_BASE_URL",
    "NVIDIA_MODEL",
    "NVIDIA_API_TOKEN",
    "NVIDIA_TIMEOUT_SECONDS",
    "NVIDIA_REASONING_BUDGET",
    "NVIDIA_ENABLE_THINKING",
    "INTERNET_ENABLED",
    "INTERNET_MODE",
]




