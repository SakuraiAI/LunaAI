from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.text_utils import clean_model_response_text, sanitize_text_for_transport


class NvidiaSpeechModel:
    SUPPORTED_AUDIO = {".wav", ".flac", ".ogg", ".opus"}

    def __init__(
        self,
        model_name: str,
        api_token: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        server: str = "grpc.nvcf.nvidia.com:443",
        function_id: str = "71203149-d3b7-4460-8231-1be2543a1fca",
        use_ssl: bool = True,
        timeout_seconds: int = 180,
        language: str = "cs-CZ",
    ) -> None:
        self.model = model_name.strip()
        self.api_token = api_token.strip()
        self.base_url = base_url.strip() or "https://integrate.api.nvidia.com/v1"
        self.server = server.strip() or "grpc.nvcf.nvidia.com:443"
        self.function_id = function_id.strip()
        self.use_ssl = bool(use_ssl)
        self.timeout_seconds = timeout_seconds
        self.language = language.strip() or "cs-CZ"

    def is_available(self) -> bool:
        return bool(self.api_token and self.server)

    def supports_path(self, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in self.SUPPORTED_AUDIO

    def _metadata(self) -> list[list[str]]:
        metadata = [["authorization", f"Bearer {self.api_token}"]]
        if self.function_id:
            metadata.insert(0, ["function-id", self.function_id])
        return metadata

    def _riva_model_name(self) -> str:
        # Hosted NVCF functions select the model through function-id. Passing a
        # model name can make Riva reject the request, so local NIMs can override
        # this later while the cloud path keeps the model field empty.
        if self.server.endswith(":443") and self.function_id:
            return ""
        return self.model

    def _load_riva_client(self) -> Any:
        try:
            import riva.client  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "NVIDIA speech-to-text needs the Python package 'nvidia-riva-client'. "
                "Install it with: python -m pip install -U nvidia-riva-client"
            ) from exc
        return riva.client

    def transcribe_audio(self, audio_file: str | Path, language: str = "") -> str:
        if not self.is_available():
            raise RuntimeError("NVIDIA speech-to-text model is not configured.")

        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise RuntimeError(f"Audio file not found: {audio_path}")
        if not self.supports_path(audio_path):
            raise RuntimeError(
                f"Unsupported audio file type: {audio_path.suffix}. "
                "Use 16-bit mono WAV, FLAC, OGG, or OPUS."
            )

        riva_client = self._load_riva_client()
        safe_language = sanitize_text_for_transport(language or self.language)

        auth = riva_client.Auth(
            use_ssl=self.use_ssl,
            uri=self.server,
            metadata_args=self._metadata(),
        )
        asr_service = riva_client.ASRService(auth)
        recognition_config = riva_client.RecognitionConfig(
            language_code=safe_language,
            model=self._riva_model_name(),
            max_alternatives=1,
            enable_automatic_punctuation=True,
            verbatim_transcripts=True,
        )
        streaming_config = riva_client.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=False,
        )

        transcripts: list[str] = []
        last_partial = ""

        try:
            with riva_client.AudioChunkFileIterator(str(audio_path), 1600, None) as audio_chunks:
                responses = asr_service.streaming_response_generator(
                    audio_chunks=audio_chunks,
                    streaming_config=streaming_config,
                )
                for response in responses:
                    for result in getattr(response, "results", []):
                        alternatives = getattr(result, "alternatives", [])
                        if not alternatives:
                            continue
                        transcript = str(getattr(alternatives[0], "transcript", "") or "").strip()
                        if not transcript:
                            continue
                        if bool(getattr(result, "is_final", False)):
                            transcripts.append(transcript)
                        else:
                            last_partial = transcript
        except Exception as exc:
            raise RuntimeError(f"NVIDIA speech-to-text failed: {exc}") from exc

        transcript = clean_model_response_text(" ".join(transcripts).strip() or last_partial)
        if not transcript.strip():
            raise RuntimeError("NVIDIA speech-to-text returned an empty transcript.")
        return transcript
