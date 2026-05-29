"""Meta WhatsApp Business Cloud API client (S5 Feature 1).

Direct Graph API integration — no Twilio. Same configuration discipline as the
other external clients: `is_configured()` gates everything and the client
no-ops cleanly without credentials so dev/CI run without a Meta app.

Three responsibilities:
    - send_text: outbound replies (POST /{phone_number_id}/messages)
    - validate_signature: verify inbound webhook authenticity (X-Hub-Signature-256)
    - verify_token: the GET webhook handshake check

Free-form text is allowed only inside the 24h customer-service window; the bot
only ever replies to an owner who just messaged it, so that holds. Proactive
out-of-window messages would need an approved template (future work).
"""

import hashlib
import hmac
from typing import Any

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

_GRAPH_BASE = "https://graph.facebook.com"
_HTTP_TIMEOUT = 10.0


def is_configured() -> bool:
    """Sending requires a token + the number id. Signature validation also
    needs the app secret, but we gate sending on these two (validation handles
    a missing secret by failing closed)."""
    s = get_settings()
    return bool(s.whatsapp_access_token and s.whatsapp_phone_number_id)


def _normalise_to(to: str) -> str:
    """Meta addresses recipients by wa_id — digits only, no '+' and no
    'whatsapp:' prefix. Inbound `from` already arrives in this shape; we strip
    defensively in case a caller passes E.164."""
    return to.strip().removeprefix("whatsapp:").lstrip("+").strip()


def send_text(*, to: str, body: str) -> str | None:
    """Send a WhatsApp text message via the Cloud API. Returns the message id,
    or None when not configured (dev/CI — log and move on). Raises only on a
    real HTTP failure so the caller can decide whether to swallow."""
    if not is_configured():
        log.info("whatsapp_skip_send", reason="not_configured")
        return None

    s = get_settings()
    url = f"{_GRAPH_BASE}/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _normalise_to(to),
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {s.whatsapp_access_token}"},
        json=payload,
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    msg_id = None
    messages = data.get("messages") if isinstance(data, dict) else None
    if isinstance(messages, list) and messages:
        msg_id = messages[0].get("id")
    log.info("whatsapp_text_sent", to_suffix=to[-4:], message_id=msg_id)
    return str(msg_id) if msg_id else None


def send_document(*, to: str, content: bytes, filename: str, caption: str = "") -> str | None:
    """Send a PDF (or other doc) via the Cloud API (S5 F1 Phase B — monthly
    report). Two steps: upload the bytes to get a media id, then send a
    document message referencing it. Returns the message id, or None when not
    configured (dev/CI no-op). Raises only on a real HTTP failure."""
    if not is_configured():
        log.info("whatsapp_skip_document", reason="not_configured")
        return None

    s = get_settings()
    base = f"{_GRAPH_BASE}/{s.whatsapp_api_version}"
    headers = {"Authorization": f"Bearer {s.whatsapp_access_token}"}

    upload = httpx.post(
        f"{base}/{s.whatsapp_phone_number_id}/media",
        headers=headers,
        data={"messaging_product": "whatsapp", "type": "application/pdf"},
        files={"file": (filename, content, "application/pdf")},
        timeout=_HTTP_TIMEOUT,
    )
    upload.raise_for_status()
    media_id = upload.json().get("id")
    if not media_id:
        return None

    document: dict[str, Any] = {"id": media_id, "filename": filename}
    if caption:
        document["caption"] = caption
    resp = httpx.post(
        f"{base}/{s.whatsapp_phone_number_id}/messages",
        headers=headers,
        json={
            "messaging_product": "whatsapp",
            "to": _normalise_to(to),
            "type": "document",
            "document": document,
        },
        timeout=_HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    messages = resp.json().get("messages") if isinstance(resp.json(), dict) else None
    msg_id = messages[0].get("id") if isinstance(messages, list) and messages else None
    log.info("whatsapp_document_sent", to_suffix=to[-4:], message_id=msg_id)
    return str(msg_id) if msg_id else None


def validate_signature(*, raw_body: bytes, signature: str | None) -> bool:
    """Verify an inbound webhook came from Meta.

    Meta signs each POST with `X-Hub-Signature-256: sha256=<hex>`, an HMAC-SHA256
    of the RAW request body keyed on the app secret. Returns False when the app
    secret isn't configured or the signature is missing/invalid — the router
    turns that into a 403. Mirrors the Stripe webhook's signature gate.
    """
    s = get_settings()
    if not s.whatsapp_app_secret or not signature:
        return False

    expected = hmac.new(
        s.whatsapp_app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    provided = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, provided)


def verify_token_matches(token: str | None) -> bool:
    """GET handshake: Meta echoes hub.verify_token; it must equal our secret.
    Constant-time compare; fails closed if the token isn't configured."""
    s = get_settings()
    if not s.whatsapp_verify_token or not token:
        return False
    return hmac.compare_digest(s.whatsapp_verify_token, token)
