import json
from importlib import import_module
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


class InternetTool:
    def __init__(self) -> None:
        settings_module = import_module("config.settings")
        settings_class = getattr(settings_module, "AppSettings")
        self.settings = settings_class()
        self.enabled = bool(self.settings.internet_enabled)
        self.internet_mode = str(self.settings.internet_mode)

    def is_enabled(self) -> bool:
        return self.enabled

    def mode(self) -> str:
        return self.internet_mode

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def set_mode(self, mode: str) -> None:
        if mode in {"manual", "auto"}:
            self.internet_mode = mode

    def status(self) -> str:
        state = "on" if self.enabled else "off"
        return f"Luna: Internet is {state}. Mode: {self.internet_mode}."

    def should_search(self, query: str) -> bool:
        if not self.is_enabled() or self.mode() != "auto":
            return False

        normalized = query.strip().lower()
        if not normalized:
            return False

        trigger_phrases = [
            "today",
            "now",
            "current",
            "latest",
            "recent",
            "news",
            "weather",
            "price",
            "stock",
            "bitcoin",
            "btc",
            "who is",
            "what time",
            "what day",
            "date today",
            "schedule",
            "version",
            "release",
            "update",
            "live",
            "currently",
            "dnes",
            "ted",
            "aktualni",
            "posledni",
            "nejnovejsi",
            "zpravy",
            "pocasi",
            "kolik je hodin",
            "jaky je dnes den",
            "jaky je dnes datum",
            "jaka je cena",
            "kurz",
        ]

        question_words = ["when", "where", "who", "what", "jak", "kdy", "kde", "kdo", "co"]
        if any(phrase in normalized for phrase in trigger_phrases):
            return True

        return normalized.endswith("?") and any(
            normalized.startswith(word + " ") for word in question_words
        )

    def search(self, query: str) -> str:
        if not self.is_enabled():
            return "Luna: Internet access is currently disabled."

        encoded_query = quote_plus(query.strip())
        url = (
            "https://api.duckduckgo.com/"
            f"?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        )
        request = Request(
            url,
            headers={
                "User-Agent": "LunaAI/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return f"Luna: Internet search failed with HTTP {error.code}."
        except URLError as error:
            return f"Luna: Internet search is unavailable right now. Details: {error.reason}"
        except Exception as error:
            return f"Luna: Internet search failed. Details: {error}"

        summary = self._summarize_payload(payload, query)
        if summary:
            return summary

        return (
            "Luna: I could not find a concise internet result for that query. "
            f"Query: {query}"
        )

    def _summarize_payload(self, payload: dict[str, Any], query: str) -> str:
        heading = str(payload.get("Heading", "")).strip()
        abstract = str(payload.get("AbstractText", "")).strip()
        answer = str(payload.get("Answer", "")).strip()
        answer_type = str(payload.get("AnswerType", "")).strip()
        source_url = str(payload.get("AbstractURL", "")).strip()

        lines: list[str] = []
        if answer:
            prefix = f"{heading}: " if heading else ""
            lines.append(prefix + answer)
            if answer_type:
                lines.append(f"Answer type: {answer_type}")

        if abstract:
            prefix = f"{heading}: " if heading else ""
            lines.append(prefix + abstract)

        related_topics = payload.get("RelatedTopics", [])
        related_lines: list[str] = []
        seen_related: set[str] = set()
        for topic in related_topics:
            item = self._extract_topic(topic)
            if not item:
                continue
            if item in seen_related:
                continue
            if source_url and source_url in item:
                continue
            related_lines.append(item)
            seen_related.add(item)
            if len(related_lines) == 2:
                break

        if related_lines:
            lines.append("Related: " + " | ".join(related_lines))

        if source_url:
            lines.append(f"Source: {source_url}")

        if not lines:
            return ""

        return f"Internet research for '{query}':\n- " + "\n- ".join(lines)

    def _extract_topic(self, topic: dict[str, Any]) -> str:
        text = str(topic.get("Text", "")).strip()
        first_url = str(topic.get("FirstURL", "")).strip()
        if text and first_url:
            return f"{text} ({first_url})"
        if text:
            return text

        nested_topics = topic.get("Topics", [])
        for nested in nested_topics:
            nested_text = str(nested.get("Text", "")).strip()
            nested_url = str(nested.get("FirstURL", "")).strip()
            if nested_text and nested_url:
                return f"{nested_text} ({nested_url})"
            if nested_text:
                return nested_text

        return ""
