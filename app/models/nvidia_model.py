from __future__ import annotations

from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]

from app.models.base_model import BaseModel
from app.core.text_utils import clean_model_response_text


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

    def is_available(self) -> bool:
        return bool(OpenAI is not None and self.api_token and self.model)

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
            messages = prompt
        else:
            messages = [{"role": "user", "content": prompt}]

        completion = self._client().chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=1,
            top_p=0.95,
            max_tokens=16384,
            extra_body={
                "reasoning_budget": self.reasoning_budget,
                "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
            },
            stream=False,
        )

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


