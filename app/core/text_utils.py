from __future__ import annotations

import re
from urllib.parse import urlparse

_MOJIBAKE_MARKERS = (
    "\u00c2",
    "\u00c3",
    "\u00c4",
    "\u00c5",
    "\u00e2",
    "\u02c7",
    "\u02d8",
    "\u02db",
    "\ufffd",
)
_CZECH_HINTS = re.compile(
    r"[\u00e1\u010d\u010f\u00e9\u011b\u00ed\u0148\u00f3\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e\u00c1\u010c\u010e\u00c9\u011a\u00cd\u0147\u00d3\u0158\u0160\u0164\u00da\u016e\u00dd\u017d]"
)
_PLACEHOLDER_DOMAINS = {
    "example.com",
    "www.example.com",
    "github.com/example-user",
    "www.github.com/example-user",
}
_PLACEHOLDER_PARTS = (
    "example-user",
    "project-name",
    "placeholder",
    "your-link-here",
)
_URL_PATTERN = re.compile(r"https?://\S+")

_COMMON_MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\ufffd": '"',
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u00a6": "...",
    "\u00c2\u00a0": " ",
    "\u00c2": "",
    "\u0102\u02c7": "\u00e1",
    "\u00c4\u0164": "\u010d",
    "\u00c4\u0179": "\u010f",
    "\u00c4\u203a": "\u011b",
    "\u0102\u00ad": "\u00ed",
    "\u0139\u0088": "\u0148",
    "\u0139\u2122": "\u0159",
    "\u0139\u02c7": "\u0161",
    "\u0139\u0104": "\u0165",
    "\u0139\u017b": "\u016f",
    "\u0102\u02dd": "\u00fd",
    "\u0139\u013e": "\u017e",
    "\u0102\u0081": "\u00c1",
    "\u00c4\u015a": "\u010c",
    "\u00c4\u017d": "\u010e",
    "\u00c4\u0161": "\u011a",
    "\u0102\u0164": "\u00cd",
    "\u0139\u2021": "\u0147",
    "\u0102\u201c": "\u00d3",
    "\u0139\u0098": "\u0158",
    "\u0139\u00a0": "\u0160",
    "\u0139\u00a4": "\u0164",
    "\u0102\u0161": "\u00da",
    "\u0139\u00ae": "\u016e",
    "\u0102\u0165": "\u00dd",
    "\u0139\u02dd": "\u017d",
    "\u00c3\u00a1": "\u00e1",
    "\u00c3\u00a9": "\u00e9",
    "\u00c3\u00ad": "\u00ed",
    "\u00c3\u00b3": "\u00f3",
    "\u00c3\u00ba": "\u00fa",
    "\u00c3\u00bd": "\u00fd",
    "\u00c3\u0081": "\u00c1",
    "\u00c3\u008d": "\u00cd",
    "\u00c3\u0093": "\u00d3",
    "\u00c3\u009a": "\u00da",
    "\u00c3\u009d": "\u00dd",
}
_SINGLE_BYTE_SOURCE_ENCODINGS = ("cp1250", "cp1252", "latin-1")


def _mojibake_score(text: str) -> int:
    score = 0
    score += text.count("\ufffd") * 12
    score += sum(text.count(marker) * 4 for marker in _MOJIBAKE_MARKERS)
    score -= len(_CZECH_HINTS.findall(text)) * 3
    if re.search(r"\u00c3[\u02c7\u00a1-\u00bf]", text):
        score += 8
    if re.search(r"\u00c4[\u02c7\u010d\u010f]", text):
        score += 8
    if re.search(r"\u00c5[\u2122\u00be\u00a1]", text):
        score += 8
    return score


def _try_utf8_redecode(text: str, source_encoding: str) -> str | None:
    try:
        return text.encode(source_encoding, errors="strict").decode("utf-8", errors="strict")
    except UnicodeError:
        return None


def repair_text(text: str) -> str:
    if not text:
        return text

    original = text.replace("\r\n", "\n")
    candidates: list[str] = []

    def _add_candidate(value: str) -> None:
        candidate = value.replace("\r\n", "\n")
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    _add_candidate(original)

    replaced = original
    for source, target in _COMMON_MOJIBAKE_REPLACEMENTS.items():
        replaced = replaced.replace(source, target)
    _add_candidate(replaced)

    if any(marker in original for marker in _MOJIBAKE_MARKERS) or any(marker in replaced for marker in _MOJIBAKE_MARKERS):
        for base in (original, replaced):
            for source_encoding in _SINGLE_BYTE_SOURCE_ENCODINGS:
                candidate = _try_utf8_redecode(base, source_encoding)
                if candidate:
                    _add_candidate(candidate)

    best = min(candidates, key=_mojibake_score)
    return best.replace("\r\n", "\n")


def strip_surrogate_codepoints(text: str) -> str:
    if not text:
        return text
    return "".join(ch for ch in text if not 0xD800 <= ord(ch) <= 0xDFFF)


def sanitize_text_for_transport(text: str) -> str:
    return strip_surrogate_codepoints(repair_text(text).replace("\r\n", "\n"))


def is_placeholder_url(url: str) -> bool:
    clean = url.strip().rstrip(".,;:!?)]}\"'")
    if not clean.lower().startswith(("http://", "https://")):
        return False
    parsed = urlparse(clean)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    joined = (host + path).strip("/")
    if host in _PLACEHOLDER_DOMAINS or joined in _PLACEHOLDER_DOMAINS:
        return True
    return any(part in clean.lower() for part in _PLACEHOLDER_PARTS)


def scrub_placeholder_urls(text: str) -> tuple[str, bool]:
    removed_any = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal removed_any
        url = match.group(0)
        if is_placeholder_url(url):
            removed_any = True
            return "[unverified link removed]"
        return url

    return _URL_PATTERN.sub(_replace, text), removed_any


def canonicalize_url(url: str) -> str:
    return url.strip().rstrip(".,;:!?)]}\"'")


def normalize_memory_entry(text: str) -> str:
    repaired = repair_text(text)
    lowered = " ".join(repaired.lower().split())
    lowered = lowered.replace("xeno model guidance:", "xeno:")
    lowered = lowered.replace("agent handoff:", "handoff:")
    lowered = lowered.replace("agent next step:", "next:")
    lowered = lowered.replace("xeno refreshed the project plan for", "xeno-refresh:")
    return lowered[:240]


def dedupe_preserve_order(items: list[str], *, normalizer=normalize_memory_entry, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        clean = repair_text(item).strip()
        if not clean:
            continue
        key = normalizer(clean)
        if key in seen:
            continue
        seen.add(key)
        output.append(clean)
        if limit is not None and len(output) >= limit:
            break
    return output


def _strip_internal_reasoning_leaks(text: str) -> str:
    cleaned = text.strip()

    final_match = re.search(r'(?:^|\n)(?:\*\*?|#+\s*)?(?:final\s+polish|final\s+answer|odpoved|finalni\s+odpoved)\s*[:\-]?\s*[\"]?(.+)', cleaned, re.IGNORECASE | re.DOTALL)
    if final_match:
        candidate = final_match.group(1).strip()
        candidate = candidate.strip('"')
        if candidate:
            return candidate

    leak_markers = (
        '* User says',
        '* Context:',
        '* The user',
        '* Persona:',
        '* Language:',
        '* Draft:',
        '*Final Polish',
        "Let's look at",
        'Wait, the prompt says',
        'I should acknowledge',
        'A good response would be',
    )
    if any(marker.lower() in cleaned.lower() for marker in leak_markers):
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        quoted_candidates: list[str] = []
        plain_candidates: list[str] = []
        for line in lines:
            stripped = line.strip('*- ').strip()
            if not stripped:
                continue
            if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 2:
                quoted_candidates.append(stripped.strip('"'))
                continue
            if any(marker.lower() in stripped.lower() for marker in leak_markers):
                continue
            if stripped.lower().startswith(('user says', 'context:', 'the user', 'persona:', 'language:', 'draft:', 'final polish')):
                continue
            if len(stripped) <= 220:
                plain_candidates.append(stripped)
        for candidate in reversed(quoted_candidates):
            if candidate:
                return candidate
        for candidate in reversed(plain_candidates):
            if candidate and not candidate.startswith(('User:', 'Assistant:')):
                return candidate

    return cleaned


def clean_model_response_text(text: str) -> str:
    cleaned = _strip_internal_reasoning_leaks(repair_text(text).strip())
    for prefix in ("Assistant: ", "Luna: "):
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(prefix).strip()

    cleaned, removed_placeholder = scrub_placeholder_urls(cleaned)
    cleaned = cleaned.replace("\r\n", "\n").strip()

    lines: list[str] = []
    seen_urls: set[str] = set()
    for raw_line in cleaned.split("\n"):
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        urls = [canonicalize_url(url) for url in _URL_PATTERN.findall(line)]
        if urls and all(url in seen_urls for url in urls) and len(line) <= 280:
            continue
        for url in urls:
            seen_urls.add(url)
        if not lines or lines[-1] != line:
            lines.append(line)

    cleaned = "\n".join(lines).strip()
    if removed_placeholder and "[unverified link removed]" in cleaned:
        cleaned += "\n\nI removed a placeholder link because it was not verified."
    return cleaned
