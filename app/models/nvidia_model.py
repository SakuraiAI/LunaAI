from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]

from app.models.base_model import BaseModel
from app.core.text_utils import clean_model_response_text, sanitize_text_for_transport


class NvidiaModel(BaseModel):
    def __init__(
        self,
        model_name: str,
        api_token: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout_seconds: int = 180,
        reasoning_budget: int = 16384,
        enable_thinking: bool = True,
    ) -> None:
        self.model = model_name.strip()
        self.api_token = api_token.strip()
        self.base_url = base_url.strip() or "https://integrate.api.nvidia.com/v1"
        self.timeout_seconds = timeout_seconds
        self.reasoning_budget = reasoning_budget
        self.enable_thinking = enable_thinking
        self.runtime_cpu_limit_percent = 100
        self.runtime_gpu_limit_percent = 100
        self.runtime_memory_limit_percent = 100

    def is_available(self) -> bool:
        return bool(OpenAI is not None and self.api_token and self.model)

    def configure_runtime_limits(
        self,
        cpu_limit_percent: int = 100,
        gpu_limit_percent: int = 100,
        memory_limit_percent: int = 100,
    ) -> None:
        self.runtime_cpu_limit_percent = max(10, min(100, int(cpu_limit_percent)))
        self.runtime_gpu_limit_percent = max(10, min(100, int(gpu_limit_percent)))
        self.runtime_memory_limit_percent = max(10, min(100, int(memory_limit_percent)))

    def _runtime_output_budget(self) -> int:
        headroom = min(
            self.runtime_cpu_limit_percent,
            self.runtime_gpu_limit_percent,
            self.runtime_memory_limit_percent,
        )
        if headroom <= 35:
            return 2048
        if headroom <= 50:
            return 4096
        if headroom <= 70:
            return 8192
        return 16384

    def _runtime_reasoning_budget(self) -> int:
        return min(self.reasoning_budget, self._runtime_output_budget())

    def _uses_simple_chat_payload(self) -> bool:
        return self.model.startswith("openai/gpt-oss")

    def _client(self) -> Any:
        if OpenAI is None:
            raise RuntimeError("Python package 'openai' is not installed.")
        if not self.api_token:
            raise RuntimeError("NVIDIA API token is empty.")
        if not self.model:
            raise RuntimeError("NVIDIA model name is empty.")
        return OpenAI(
            base_url=self.base_url,
            api_key=self.api_token,
            timeout=self.timeout_seconds,
        )

    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        if not self.is_available():
            raise RuntimeError("NVIDIA model is not configured or available.")

        messages: list[dict[str, str]]
        if isinstance(prompt, list):
            messages = [
                {
                    "role": str(item.get("role", "user") or "user"),
                    "content": sanitize_text_for_transport(str(item.get("content", "") or "")),
                }
                for item in prompt
            ]
        else:
            messages = [{"role": "user", "content": sanitize_text_for_transport(prompt)}]

        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 1,
            "top_p": 1 if self._uses_simple_chat_payload() else 0.95,
            "max_tokens": min(4096, self._runtime_output_budget()) if self._uses_simple_chat_payload() else self._runtime_output_budget(),
            "stream": False,
        }
        if not self._uses_simple_chat_payload():
            request_kwargs["extra_body"] = {
                "reasoning_budget": self._runtime_reasoning_budget(),
                "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
            }

        completion = self._client().chat.completions.create(**request_kwargs)

        message = completion.choices[0].message if completion.choices else None
        content = getattr(message, "content", "") if message is not None else ""
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                text = getattr(item, "text", None)
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            content = "\n".join(parts)
        if not isinstance(content, str):
            content = str(content or "")
        return clean_model_response_text(content)


