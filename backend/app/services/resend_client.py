from typing import Any, cast

import resend
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


def configure_resend() -> None:
    settings = get_settings()
    if settings.resend_api_key:
        resend.api_key = settings.resend_api_key


def is_configured() -> bool:
    return bool(get_settings().resend_api_key)


def send(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
    tags: list[dict[str, str]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> str | None:
    """Send a transactional email via Resend.

    Returns the Resend message id on success, or None when Resend isn't
    configured (dev/test envs without a key — we want code to run normally,
    just without actually sending). Raises on actual send failures so the
    caller can decide whether to swallow or surface.

    `tags` are attached for Resend dashboard filtering (e.g. `welcome`,
    `payment_succeeded`) — handy when triaging deliverability issues.

    `attachments` is forwarded straight to the Resend API. Each entry is a
    dict with `filename` and `content` (already-encoded per Resend's contract
    — see `build_pdf_attachment`). We don't transform the list here so
    callers can keep one schema and add new attachment types without
    changing this layer.
    """
    if not is_configured():
        log.info("resend_skip_send", to_domain=_email_domain(to), reason="no_key")
        return None

    configure_stripe_safe()

    settings = get_settings()
    payload: dict[str, Any] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if tags:
        payload["tags"] = tags
    if attachments:
        payload["attachments"] = attachments

    # The SDK types `send` with a TypedDict (SendParams) but accepts plain
    # dicts at runtime. Building a dict here keeps the function tolerant of
    # SDK type-stub churn between versions.
    resp = resend.Emails.send(cast(Any, payload))
    # The SDK returns a dict {"id": "..."} on success. Be defensive about
    # shape — the field has been stable but we don't want to crash on a
    # future SDK update.
    msg_id = resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", None)
    log.info(
        "resend_email_sent",
        to_domain=_email_domain(to),
        subject_preview=subject[:60],
        message_id=msg_id,
    )
    return str(msg_id) if msg_id else None


def configure_stripe_safe() -> None:
    """Idempotent: set the API key if not yet set this process. Resend's SDK
    uses a module-level global, so repeated assignment is harmless but noisy."""
    if not getattr(resend, "api_key", None):
        configure_resend()


def _email_domain(email: str) -> str:
    """Log only the domain — full address in logs is unnecessary PII."""
    if "@" not in email:
        return "unknown"
    return email.split("@", 1)[1].lower()


def build_pdf_attachment(*, filename: str, pdf_bytes: bytes) -> dict[str, Any]:
    """Resend attachment payload for a PDF.

    Resend's HTTP API accepts `content` as a base64 string OR as an array of
    integers. The Python SDK JSON-encodes whatever we pass; a list of ints is
    huge over the wire and many proxies choke on it, so base64 wins on both
    size and compatibility. The MIME type is fixed because every caller of
    this helper today is the monthly PDF — when we add CSV/HTML attachments
    we should make it explicit (and probably split this into a generic
    `build_attachment(content_type=...)`).
    """
    import base64

    return {
        "filename": filename,
        "content": base64.b64encode(pdf_bytes).decode("ascii"),
        "content_type": "application/pdf",
    }
