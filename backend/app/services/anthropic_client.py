"""Anthropic client for AI-drafted review replies (S5 Feature 3).

Same configuration discipline as the other external clients: `is_configured()`
gates everything and there are no module-level SDK side effects, so importing
this in dev/CI without a key is harmless.

The model and key come from settings. Callers MUST check `is_configured()`
first; calling unconfigured raises (it's a programming error, not a runtime
condition we degrade on).
"""

from typing import Any, cast

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

# A review reply is short; cap output so a runaway generation can't balloon
# cost or latency.
MAX_TOKENS = 1024


def is_configured() -> bool:
    return bool(get_settings().anthropic_api_key)


def generate_text(*, system: str, user_text: str, max_tokens: int = MAX_TOKENS) -> str:
    """One-shot generation (no tools) — used by Feature 3 to draft a review
    reply. Returns the text answer. Raises RuntimeError if unconfigured; the
    caller gates on `is_configured()` (a no-op draft is useless, so we don't
    invent one)."""
    if not is_configured():
        raise RuntimeError("anthropic_client.generate_text called unconfigured")

    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=cast(Any, [{"role": "user", "content": user_text}]),
    )
    return _extract_text(resp)


def _extract_text(resp: Any) -> str:
    """Concatenate text blocks from a final (non-tool) response."""
    parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "\n".join(p for p in parts if p).strip()
