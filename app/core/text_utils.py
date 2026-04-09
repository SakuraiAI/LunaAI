from __future__ import annotations

import re
from urllib.parse import urlparse

_BAD_MARKERS = ("?", "?", "?", "?", "?", "?", "?")
_CZECH_HINTS = "aeiouycdenrstzAEIOUYCDENRSTZ"
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
    "M??m": "Mam",
    "D??kuji": "Dekuji",
    "P????stup": "Pristup",
    "P????stup byl odep??en": "Pristup byl odepren",
    "odep??en": "odepren",
    "P??": "Pr",
    "??": "a",
    "??": "e",
    "??": "e",
    "??": "i",
    "??": "o",
    "??": "u",
    "??": "u",
    "??": "y",
    "??": "c",
    "??": "d",
    "??": "n",
    "??": "r",
    "??": "s",
    "??": "t",
    "??": "z",
    "??": "A",
    "??": "E",
    "??": "E",
    "??": "I",
    "??": "O",
    "??": "U",
    "??": "U",
    "??": "Y",
    "??": "C",
    "??": "D",
    "??": "N",
    "??": "R",
    "??": "S",
    "??": "T",
    "??": "Z",
    "???": "'",
    "???": """,
    "???": """,
    "???": "-",
    "???": "-",
    "???": "...",
}

def _mojibake_score(text: str) -> int:
    score = 0
    score += sum(text.count(marker) * 4 for marker in _BAD_MARKERS)
    score -= sum(text.count(ch) for ch in _CZECH_HINTS)
    return score

def repair_text(text: str) -> str:
    if not text:
        return text

    repaired = text
    for source, target in _COMMON_MOJIBAKE_REPLACEMENTS.items():
        repaired = repaired.replace(source, target)

    candidates = [repaired]
    for source_encoding in ("latin-1", "cp1252"):
        try:
            candidate = repaired.encode(source_encoding, errors="ignore").decode("utf-8", errors="ignore")
        except Exception:
            continue
        if candidate:
            candidates.append(candidate)

    best = min(candidates, key=_mojibake_score)
    return best.replace("\r\n", "\n")

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
        'Let''s look at',
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


