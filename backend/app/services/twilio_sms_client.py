"""Twilio SMS client (Sprint 5.6 — customer phone OTP).

Same configuration discipline as the other external clients (resend, Meta
WhatsApp, Google): `is_configured()` gates everything and the client no-ops
cleanly without credentials so dev/CI run without a Twilio account.

Single responsibility: send a transactional SMS via the Twilio REST API.
"""

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_BASE = "https://api.twilio.com/2010-04-01"
_HTTP_TIMEOUT = 10.0


def is_configured() -> bool:
    """Sending needs the account SID, auth token, and a verified from-number."""
    s = get_settings()
    return bool(s.twilio_account_sid and s.twilio_auth_token and s.twilio_sms_from)


def send_sms(*, to: str, body: str) -> str | None:
    """Send an SMS via Twilio. Returns the message SID, or None when not
    configured (dev/CI — log and move on). Raises only on a real HTTP failure
    so the caller can decide whether to swallow."""
    if not is_configured():
        log.info("sms_skip_send", reason="not_configured")
        return None

    s = get_settings()
    resp = httpx.post(
        f"{_BASE}/Accounts/{s.twilio_account_sid}/Messages.json",
        auth=(s.twilio_account_sid, s.twilio_auth_token),
        data={"From": s.twilio_sms_from, "To": to, "Body": body},
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    sid = resp.json().get("sid")
    log.info("sms_sent", sid=sid)
    return str(sid) if sid else None
