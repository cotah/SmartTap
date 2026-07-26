from typing import Any

import stripe
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services import (
    instagram_dm_service,
    meta_client,
    webhook_service,
    whatsapp_bot_service,
    whatsapp_client,
)
from app.services.instagram_dm_service import InstagramEvent

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


@router.get("/webhooks/instagram")
async def instagram_webhook_verify(request: Request) -> Response:
    """Meta webhook verification handshake for the Instagram DM assistant.
    Same hub.challenge dance as the WhatsApp webhook, but checked against this
    Meta app's META_VERIFY_TOKEN."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and meta_client.verify_token_matches(token):
        return PlainTextResponse(content=challenge, status_code=200)
    log.warning("instagram_webhook_verify_failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/instagram")
async def instagram_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> Response:
    """Inbound Instagram DMs + story mentions from the Meta Graph API.

    Same discipline as the WhatsApp webhook: validate X-Hub-Signature-256
    (HMAC of the RAW body, this app's META_APP_SECRET), dispatch each event to
    the DM service, and never 5xx on a bot error — Meta would retry and the
    customer would get duplicate replies.
    """
    raw = await request.body()
    if not meta_client.validate_signature(raw_body=raw, signature=x_hub_signature_256):
        log.warning("instagram_webhook_invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON") from None

    for event in _extract_instagram_events(payload):
        try:
            instagram_dm_service.handle_event(event)
        except Exception as exc:  # belt and braces — the service already catches
            log.exception("instagram_event_failed", error=str(exc))

    return Response(status_code=200)


def _extract_instagram_events(payload: dict[str, Any]) -> list[InstagramEvent]:
    """Pull InstagramEvents out of a Meta Instagram webhook payload.

    Shape: entry[].id = IG business account id, entry[].messaging[] with
    sender.id + message.{text, is_echo, attachments[]}. A story mention
    arrives as an attachment of type "story_mention" on the SAME messages
    webhook. Echoes of our own outbound replies carry is_echo=true and are
    skipped (anti-loop). Defensive against missing keys — a malformed payload
    yields no events rather than raising.
    """
    out: list[InstagramEvent] = []
    if not isinstance(payload, dict):
        return out
    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        ig_account_id = entry.get("id")
        if not isinstance(ig_account_id, str):
            continue
        for item in entry.get("messaging", []) or []:
            if not isinstance(item, dict):
                continue
            message = item.get("message") or {}
            if not isinstance(message, dict) or message.get("is_echo"):
                continue
            sender_id = (item.get("sender") or {}).get("id")
            if not isinstance(sender_id, str) or sender_id == ig_account_id:
                continue  # no sender, or our own account — skip
            text = message.get("text")
            attachments = message.get("attachments") or []
            is_story_mention = any(
                isinstance(a, dict) and a.get("type") == "story_mention"
                for a in attachments
            )
            out.append(
                InstagramEvent(
                    ig_account_id=ig_account_id,
                    sender_id=sender_id,
                    text=text if isinstance(text, str) else None,
                    is_story_mention=is_story_mention,
                )
            )
    return out


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
