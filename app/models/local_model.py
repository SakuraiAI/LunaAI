import ast
import json
from http.client import RemoteDisconnected
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.models.base_model import BaseModel


class LocalModel(BaseModel):
    def __init__(
        self,
        provider: str = "lm_studio",
        model_name: str = "google/gemma-3-4b",
        base_url: str = "http://127.0.0.1:1234/api/v1/chat",
        api_token: str = "",
        timeout_seconds: int = 180,
    ) -> None:
        self.provider = provider
        self.model = model_name
        self.url = base_url
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def _extract_output_text(self, data: dict) -> str:
        output = data.get("output", "")

        if isinstance(output, str):
            return output.strip()

        if isinstance(output, list) and output:
            first_item = output[0]
            if isinstance(first_item, dict):
                content = first_item.get("content", "")
                if isinstance(content, str):
                    return content.strip()

        raise KeyError("output")

    def _clean_response_text(self, response_text: str) -> str:
        cleaned = response_text.strip()

        if cleaned.startswith("Assistant: "):
            cleaned = cleaned.removeprefix("Assistant: ").strip()

        if cleaned.startswith("[{"):
            try:
                parsed = ast.literal_eval(cleaned)
            except (ValueError, SyntaxError):
                parsed = None

            if isinstance(parsed, list) and parsed:
                first_item = parsed[0]
                if isinstance(first_item, dict):
                    content = first_item.get("content", "")
                    if isinstance(content, str):
                        cleaned = content.strip()

        if cleaned.startswith("Assistant: "):
            cleaned = cleaned.removeprefix("Assistant: ").strip()

        cleaned = cleaned.replace("\r\n", "\n").strip()
        return cleaned

    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        system_prompt = "You are Luna."
        input_text = prompt if isinstance(prompt, str) else ""

        if isinstance(prompt, list):
            input_parts: list[str] = []
            for message in prompt:
                role = message.get("role", "user")
                content = message.get("content", "")
                if role == "system":
                    system_prompt = content
                elif role == "assistant":
                    input_parts.append(f"Assistant: {content}")
                else:
                    input_parts.append(f"User: {content}")
            input_text = "\n".join(input_parts)

        payload = {
            "model": self.model,
            "system_prompt": system_prompt,
            "input": input_text,
            "temperature": 0.1,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))

            response_text = self._extract_output_text(data)
            response_text = self._clean_response_text(response_text)
            if "google" in response_text.lower():
                response_text = response_text.replace("Google", "LunaAI system")

            return response_text
        except HTTPError as error:
            try:
                error_body = error.read().decode("utf-8", errors="replace")
            except Exception:
                error_body = ""
            return f"Luna: LM Studio returned HTTP {error.code}. Details: {error_body or error}"
        except URLError as error:
            return (
                "Luna: LM Studio is not reachable. "
                f"Make sure the LM Studio server is running and reachable at {self.url}. "
                f"Details: {error}"
            )
        except RemoteDisconnected:
            return (
                "Luna: LM Studio accepted the connection but closed it without a response. "
                f"Check that the model is fully loaded, the server is running, and the endpoint matches {self.url}."
            )
        except TimeoutError:
            return (
                "Luna: LM Studio took too long to answer after "
                f"{self.timeout_seconds} seconds. The model may still be loading, the first reply may still be warming up, "
                "or the selected model is too heavy for the current machine."
            )
        except (KeyError, json.JSONDecodeError) as error:
            return f"Luna: Invalid response from local model -> {error}"
        except Exception as error:
            return f"Luna: Unexpected local model error -> {error}"

