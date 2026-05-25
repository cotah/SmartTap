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
