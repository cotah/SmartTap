from typing import Any, cast

import stripe
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


def configure_stripe() -> None:
    settings = get_settings()
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key


def is_configured() -> bool:
    return bool(get_settings().stripe_secret_key)


def create_customer(
    *,
    tenant_id: str,
    email: str | None,
    name: str,
) -> str | None:
    """Create a Stripe Customer for a tenant and return its id.

    Returns None when Stripe is not configured (dev/test envs without keys) so
    callers can proceed without billing wired up.

    Uses tenant_id as the idempotency key so a retry never creates a duplicate
    customer. Stores tenant_id in metadata so support can cross-reference.
    """
    if not is_configured():
        log.info("stripe_skip_create_customer", tenant_id=tenant_id, reason="no_key")
        return None

    configure_stripe()
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"tenant_id": tenant_id},
        idempotency_key=f"tenant-{tenant_id}-create",
    )
    cid = customer.get("id") if isinstance(customer, dict) else customer.id
    log.info("stripe_customer_created", tenant_id=tenant_id, stripe_customer_id=cid)
    return str(cid) if cid else None


def create_checkout_session(
    *,
    tenant_id: str,
    customer_id: str,
    recurring_price_id: str,
    setup_price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session in subscription mode with a one-time
    setup fee added to the first invoice. Returns the hosted Checkout URL.

    Raises RuntimeError when Stripe is not configured — the caller validates
    that beforehand.
    """
    if not is_configured():
        raise RuntimeError("Stripe not configured (STRIPE_SECRET_KEY missing)")
    configure_stripe()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[
            {"price": recurring_price_id, "quantity": 1},
            {"price": setup_price_id, "quantity": 1},
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": tenant_id},
        subscription_data={"metadata": {"tenant_id": tenant_id}},
        allow_promotion_codes=True,
    )
    url = session.get("url") if isinstance(session, dict) else session.url
    log.info(
        "stripe_checkout_session_created",
        tenant_id=tenant_id,
        session_id=session.get("id") if isinstance(session, dict) else session.id,
    )
    if not url:
        raise RuntimeError("Stripe Checkout Session did not return a url")
    return str(url)


def create_billing_portal_session(
    *,
    customer_id: str,
    return_url: str,
) -> str:
    """Create a Stripe Customer Portal session and return the hosted URL.

    The portal handles plan changes, payment method updates, invoice downloads,
    and cancellation — all on Stripe-hosted pages. We never touch payment data.
    """
    if not is_configured():
        raise RuntimeError("Stripe not configured (STRIPE_SECRET_KEY missing)")
    configure_stripe()

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    url = session.get("url") if isinstance(session, dict) else session.url
    log.info(
        "stripe_portal_session_created",
        customer_id=customer_id,
        session_id=session.get("id") if isinstance(session, dict) else session.id,
    )
    if not url:
        raise RuntimeError("Stripe Portal Session did not return a url")
    return str(url)


def retrieve_subscription(subscription_id: str) -> dict[str, Any] | None:
    """Fetch a Stripe Subscription. Returns None if Stripe says it doesn't exist
    (e.g. left over from a different Stripe environment). Other Stripe errors
    propagate so the caller can decide whether to retry or surface to the user.

    Returns a plain dict so callers don't depend on stripe-python's StripeObject
    in their signatures or tests.
    """
    if not is_configured():
        return None
    configure_stripe()
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
    except stripe.InvalidRequestError as exc:
        if "No such subscription" in str(exc):
            log.warning(
                "stripe_subscription_not_found",
                subscription_id=subscription_id,
            )
            return None
        raise
    # StripeObject is itself a dict subclass; expose it as a plain dict so
    # callers don't have to import StripeObject types.
    return cast(dict[str, Any], sub)
