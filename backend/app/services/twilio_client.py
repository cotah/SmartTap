"""Twilio WhatsApp client (S5 Feature 1).

Same shape as `resend_client`: `is_configured()` gates everything, and the
client no-ops cleanly when credentials are absent so dev/CI run without a
Twilio account. Two responsibilities:

    - send_whatsapp: outbound replies via the Twilio REST API
    - validate_signature: verify inbound webhook authenticity

Dev points TWILIO_WHATSAPP_FROM at the Sandbox sender; production swaps it for
the Meta-approved sender — no code change (umbrella spec).
"""

from typing import Any

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


def is_configured() -> bool:
    s = get_settings()
    return bool(s.twilio_account_sid and s.twilio_auth_token and s.twilio_whatsapp_from)


def _normalise_to(to: str) -> str:
    """Twilio WhatsApp addresses are prefixed `whatsapp:`. Inbound `From`
    already carries it; outbound `to` we build from a bare E.164 number. Accept
    either and always return the prefixed form."""
    to = to.strip()
    return to if to.startswith("whatsapp:") else f"whatsapp:{to}"


def send_whatsapp(*, to: str, body: str) -> str | None:
    """Send a WhatsApp message. Returns the Twilio message SID, or None when
    Twilio isn't configured (dev/CI — we log and move on). Raises only on a
    real send failure so the caller can decide whether to swallow."""
    if not is_configured():
        log.info("twilio_skip_send", reason="not_configured")
        return None

    from twilio.rest import Client

    s = get_settings()
    client = Client(s.twilio_account_sid, s.twilio_auth_token)
    msg = client.messages.create(
        from_=_normalise_to(s.twilio_whatsapp_from),
        to=_normalise_to(to),
        body=body,
    )
    sid = getattr(msg, "sid", None)
    log.info("twilio_whatsapp_sent", to_suffix=to[-4:], sid=sid)
    return str(sid) if sid else None


def validate_signature(*, url: str, params: dict[str, Any], signature: str | None) -> bool:
    """Verify an inbound webhook came from Twilio.

    Twilio signs each request with HMAC-SHA1 over the full URL + sorted POST
    params, sent in `X-Twilio-Signature`. We validate with the SDK's
    RequestValidator (keyed on the auth token). Returns False when Twilio isn't
    configured or the signature is missing/invalid — the router turns that into
    a 403. Mirrors the Stripe webhook's signature gate."""
    if not is_configured() or not signature:
        return False

    from twilio.request_validator import RequestValidator

    s = get_settings()
    validator = RequestValidator(s.twilio_auth_token)
    return bool(validator.validate(url, params, signature))
