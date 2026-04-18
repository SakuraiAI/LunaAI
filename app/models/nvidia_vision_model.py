from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from urllib import error, request

from app.core.text_utils import clean_model_response_text


class NvidiaVisionModel:
    SUPPORTED_MEDIA: dict[str, tuple[str, str]] = {
        ".png": ("image/png", "image_url"),
        ".jpg": ("image/jpeg", "image_url"),
        ".jpeg": ("image/jpeg", "image_url"),
        ".webp": ("image/webp", "image_url"),
        ".mp4": ("video/mp4", "video_url"),
        ".webm": ("video/webm", "video_url"),
        ".mov": ("video/mov", "video_url"),
    }

    def __init__(
        self,
        model_name: str,
        api_token: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout_seconds: int = 180,
    ) -> None:
        self.model = model_name.strip()
        self.api_token = api_token.strip()
        self.base_url = base_url.strip() or "https://integrate.api.nvidia.com/v1"
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        return bool(self.model and self.api_token)

    def supports_path(self, file_path: str | Path) -> bool:
        suffix = Path(file_path).suffix.lower()
        return suffix in self.SUPPORTED_MEDIA

    def _endpoint(self) -> str:
        normalized = self.base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    def _media_descriptor(self, path: Path) -> tuple[str, str]:
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_MEDIA:
            raise ValueError(f"Unsupported media type for {path.name}")
        return self.SUPPORTED_MEDIA[suffix]

    def _encode_media_base64(self, media_file: Path) -> str:
        return base64.b64encode(media_file.read_bytes()).decode("utf-8")

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return ""
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return ""
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        if isinstance(content, str):
            return clean_model_response_text(content)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            return clean_model_response_text("\n".join(parts))
        return clean_model_response_text(str(content or ""))

    def analyze_media(self, query: str, media_files: list[str] | list[Path]) -> str:
        if not self.is_available():
            raise RuntimeError("NVIDIA vision model is not configured.")

        paths = [Path(item) for item in media_files]
        if not paths:
            raise RuntimeError("No media files were provided to the vision model.")

        has_video = False
        content: list[dict[str, Any]] = [{"type": "text", "text": query.strip() or "Describe the scene."}]

        for media_file in paths:
            if not media_file.exists():
                raise RuntimeError(f"Media file not found: {media_file}")
            mime_type, media_type = self._media_descriptor(media_file)
            if media_type == "video_url":
                has_video = True
            base64_data = self._encode_media_base64(media_file)
            content.append(
                {
                    "type": media_type,
                    media_type: {
                        "url": f"data:{mime_type};base64,{base64_data}",
                    },
                }
            )

        if has_video and len(paths) > 1:
            raise RuntimeError("Only a single video can be analyzed at once.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "/no_think" if has_video else "/think",
                },
                {
                    "role": "user",
                    "content": content,
                },
            ],
            "temperature": 1,
            "top_p": 1,
            "max_tokens": 4096,
            "stream": False,
        }

        req = request.Request(
            self._endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as http_error:
            detail = http_error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"NVIDIA vision model returned HTTP {http_error.code}. Details: {detail}") from http_error
        except error.URLError as url_error:
            raise RuntimeError(f"NVIDIA vision model is not reachable. Details: {url_error}") from url_error

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as json_error:
            raise RuntimeError("NVIDIA vision model returned invalid JSON.") from json_error

        content_text = self._extract_content(parsed)
        if not content_text.strip():
            raise RuntimeError("NVIDIA vision model returned an empty response.")
        return content_text
