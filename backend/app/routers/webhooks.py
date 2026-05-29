from typing import Any

import stripe
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services import webhook_service, whatsapp_bot_service, whatsapp_client

router = APIRouter(tags=["webhooks"])
log = structlog.get_logger(__name__)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")
    if stripe_signature is None:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except (stripe.SignatureVerificationError, ValueError) as exc:
        log.warning("stripe_webhook_invalid", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    log.info("stripe_event_received", event_type=event["type"], event_id=event["id"])

    try:
        webhook_service.handle(event)
    except Exception as exc:
        # Infra-level failure (DB down, bug). Returning 5xx tells Stripe to
        # retry with exponential backoff (up to 3 days). Expected data issues
        # (unknown tenant, unknown price) are swallowed inside the handler so
        # they don't trigger a retry loop.
        log.exception(
            "stripe_webhook_handler_failed",
            event_id=event["id"],
            event_type=event["type"],
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Webhook handler error") from exc

    return {"received": True}


@router.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(request: Request) -> Response:
    """Meta webhook verification handshake (S5 Feature 1).

    When the webhook is configured in the Meta app, Meta sends a GET with
    `hub.mode=subscribe`, `hub.verify_token=<our secret>`, `hub.challenge=<n>`.
    We echo the challenge as plain text iff the verify token matches our
    `WHATSAPP_VERIFY_TOKEN`; otherwise 403. The param names contain dots, so we
    read them off the query string directly.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and whatsapp_client.verify_token_matches(token):
        return PlainTextResponse(content=challenge, status_code=200)
    log.warning("whatsapp_webhook_verify_failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> Response:
    """Inbound WhatsApp messages from the Meta Cloud API (S5 Feature 1).

    Meta POSTs JSON. We validate `X-Hub-Signature-256` (HMAC-SHA256 of the RAW
    body, app secret) — same spirit as the Stripe webhook — then dispatch each
    text message to the bot service and reply via the Cloud API. Status
    callbacks (delivered/read) carry no `messages` and are acknowledged with a
    200 without dispatching. We never 5xx on a bot error — Meta would retry and
    the owner would get duplicate replies.
    """
    raw = await request.body()
    if not whatsapp_client.validate_signature(raw_body=raw, signature=x_hub_signature_256):
        log.warning("whatsapp_webhook_invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    for from_number, body in _extract_text_messages(payload):
        try:
            reply = whatsapp_bot_service.handle_inbound(from_number, body)
        except Exception as exc:
            log.exception("whatsapp_bot_failed", error=str(exc))
            continue
        if reply:
            whatsapp_client.send_text(to=from_number, body=reply)

    return Response(status_code=200)


def _extract_text_messages(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Pull (from_wa_id, text_body) pairs out of a Meta webhook payload.

    Shape: entry[].changes[].value.messages[]. We only handle text messages;
    status callbacks (value.statuses) and non-text message types are skipped.
    Defensive against missing keys — a malformed payload yields no messages
    rather than raising.
    """
    out: list[tuple[str, str]] = []
    if not isinstance(payload, dict):
        return out
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}
            for message in value.get("messages", []) or []:
                if message.get("type") != "text":
                    continue
                from_number = message.get("from")
                body = (message.get("text") or {}).get("body")
                if isinstance(from_number, str) and isinstance(body, str):
                    out.append((from_number, body))
    return out
