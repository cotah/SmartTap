import stripe
import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.services import webhook_service

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
