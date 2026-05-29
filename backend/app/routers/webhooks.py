import stripe
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.config import get_settings
from app.services import twilio_client, webhook_service, whatsapp_bot_service

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


@router.post("/webhooks/twilio/whatsapp")
async def twilio_whatsapp_webhook(
    request: Request,
    x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
) -> Response:
    """Inbound WhatsApp messages from Twilio (S5 Feature 1).

    Twilio POSTs application/x-www-form-urlencoded with `From` (whatsapp:+...)
    and `Body`. We validate the signature (same spirit as the Stripe webhook),
    hand the message to the bot service, and send the reply via the Twilio REST
    API — so we return an empty 200 (NOT TwiML) to avoid double-replying.

    The signature is computed over the exact public URL Twilio called. Railway
    terminates TLS at the edge, so we rebuild it from the Host header forced to
    https rather than trusting the internal scheme.
    """
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}

    host = request.headers.get("host", "")
    url = f"https://{host}{request.url.path}"

    if not twilio_client.validate_signature(
        url=url, params=params, signature=x_twilio_signature
    ):
        log.warning("twilio_webhook_invalid_signature")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    from_number = params.get("From", "")
    body = params.get("Body", "")
    if not from_number:
        raise HTTPException(status_code=400, detail="Missing From")

    try:
        reply = whatsapp_bot_service.handle_inbound(from_number, body)
    except Exception as exc:
        # Never 5xx back to Twilio for a bot error — it would retry and the
        # owner would get duplicate replies. Log and acknowledge.
        log.exception("whatsapp_bot_failed", error=str(exc))
        return Response(status_code=200)

    if reply:
        twilio_client.send_whatsapp(to=from_number, body=reply)

    return Response(status_code=200)
