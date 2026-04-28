from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

from app.core.text_utils import sanitize_text_for_transport


class NvidiaTtsModel:
    def __init__(
        self,
        model_name: str,
        api_token: str,
        server: str = "grpc.nvcf.nvidia.com:443",
        function_id: str = "877104f7-e885-42b9-8de8-f6e4c6303969",
        use_ssl: bool = True,
        timeout_seconds: int = 180,
        language: str = "en-US",
        voice: str = "Magpie-Multilingual.EN-US.Aria",
        sample_rate_hz: int = 22050,
    ) -> None:
        self.model = model_name.strip()
        self.api_token = api_token.strip()
        self.server = server.strip() or "grpc.nvcf.nvidia.com:443"
        self.function_id = function_id.strip()
        self.use_ssl = bool(use_ssl)
        self.timeout_seconds = timeout_seconds
        self.language = language.strip() or "en-US"
        self.voice = voice.strip() or "Magpie-Multilingual.EN-US.Aria"
        self.sample_rate_hz = max(8000, int(sample_rate_hz or 22050))

    def is_available(self) -> bool:
        return bool(self.api_token and self.server and self.function_id)

    def _metadata(self) -> list[list[str]]:
        return [
            ["function-id", self.function_id],
            ["authorization", f"Bearer {self.api_token}"],
        ]

    def _load_riva_client(self) -> Any:
        try:
            import riva.client  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "NVIDIA text-to-speech needs the Python package 'nvidia-riva-client'. "
                "Install it with: python -m pip install -U nvidia-riva-client"
            ) from exc
        return riva.client

    def _write_linear_pcm_wav(self, audio_bytes: bytes, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate_hz)
            wav_file.writeframes(audio_bytes)

    def synthesize_to_file(
        self,
        text: str,
        output_path: str | Path,
        *,
        language: str = "",
        voice: str = "",
    ) -> Path:
        if not self.is_available():
            raise RuntimeError("NVIDIA text-to-speech model is not configured.")

        safe_text = sanitize_text_for_transport(text).strip()
        if not safe_text:
            raise RuntimeError("Missing text for text-to-speech.")

        riva_client = self._load_riva_client()
        auth = riva_client.Auth(
            use_ssl=self.use_ssl,
            uri=self.server,
            metadata_args=self._metadata(),
        )
        tts_service = riva_client.SpeechSynthesisService(auth)

        try:
            response = tts_service.synthesize(
                safe_text,
                voice_name=(voice or self.voice),
                language_code=(language or self.language),
                encoding=riva_client.AudioEncoding.LINEAR_PCM,
                sample_rate_hz=self.sample_rate_hz,
            )
        except Exception as exc:
            raise RuntimeError(f"NVIDIA text-to-speech failed: {exc}") from exc

        audio_bytes = bytes(getattr(response, "audio", b"") or b"")
        if not audio_bytes:
            raise RuntimeError("NVIDIA text-to-speech returned empty audio.")

        output = Path(output_path)
        self._write_linear_pcm_wav(audio_bytes, output)
        return output
