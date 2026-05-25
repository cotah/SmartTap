from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from app.config import get_settings
from app.db import tenants
from app.errors import BusinessError, NotFoundError
from app.schemas.billing import SubscriptionSummary
from app.services import stripe_client
from app.services.trial_service import compute_trial_status

log = structlog.get_logger(__name__)

BillingPlan = Literal["review", "loyalty", "pro", "network"]


class NoCustomerError(BusinessError):
    status_code = 422
    code = "no_stripe_customer"


class BillingNotConfiguredError(BusinessError):
    status_code = 503
    code = "billing_not_configured"


class MissingPriceError(BusinessError):
    status_code = 500
    code = "missing_price"


@dataclass(frozen=True)
class PlanPrices:
    recurring: str
    setup: str


def _prices_for_plan(plan: BillingPlan) -> PlanPrices:
    s = get_settings()
    table: dict[BillingPlan, PlanPrices] = {
        "review": PlanPrices(s.stripe_price_review, s.stripe_price_review_setup),
        "loyalty": PlanPrices(s.stripe_price_loyalty, s.stripe_price_loyalty_setup),
        "pro": PlanPrices(s.stripe_price_pro, s.stripe_price_pro_setup),
        "network": PlanPrices(s.stripe_price_network, s.stripe_price_network_setup),
    }
    prices = table[plan]
    if not prices.recurring or not prices.setup:
        raise MissingPriceError(
            f"Price IDs for plan '{plan}' are not configured",
            detail={"plan": plan},
        )
    return prices


def _ensure_stripe_customer(tenant: dict, email: str | None) -> str:
    """Returns the tenant's stripe_customer_id, creating one on demand.

    Bootstrap-time creation is best-effort (W1); if it failed back then we
    backfill here on the first upgrade attempt. Persists the new id on success.
    """
    existing = tenant.get("stripe_customer_id")
    if existing:
        return str(existing)

    new_id = stripe_client.create_customer(
        tenant_id=tenant["id"],
        email=email,
        name=tenant["name"],
    )
    if new_id is None:
        raise BillingNotConfiguredError(
            "Stripe is not configured on this environment",
            detail={"reason": "no_stripe_key"},
        )
    tenants.update(tenant["id"], {"stripe_customer_id": new_id})
    return new_id


def _is_no_such_customer(exc: Exception) -> bool:
    """Stripe raises InvalidRequestError("No such customer: cus_...") when the
    stored id was created against different API keys (e.g. live vs test) or
    the customer was deleted in the dashboard. We match by message so we don't
    depend on the exact stripe-python error class layout across versions."""
    return "No such customer" in str(exc)


def create_checkout_session(
    *,
    tenant_id: str,
    plan: BillingPlan,
    email: str | None,
    success_url: str,
    cancel_url: str,
) -> str:
    if not stripe_client.is_configured():
        raise BillingNotConfiguredError(
            "Stripe is not configured on this environment",
            detail={"reason": "no_stripe_key"},
        )

    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    prices = _prices_for_plan(plan)
    customer_id = _ensure_stripe_customer(tenant, email)

    try:
        url = stripe_client.create_checkout_session(
            tenant_id=tenant_id,
            customer_id=customer_id,
            recurring_price_id=prices.recurring,
            setup_price_id=prices.setup,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as exc:
        if not _is_no_such_customer(exc):
            raise
        # Stale customer id (created in a different Stripe env, or deleted in
        # the dashboard). Reset the stored id, create a fresh customer against
        # the current keys, and retry exactly once. A second failure propagates.
        log.warning(
            "stripe_stale_customer_id_recovered",
            tenant_id=tenant_id,
            old_customer_id=customer_id,
        )
        # Use the row returned by update() rather than re-fetching — avoids
        # both a needless round-trip and any chance of read-your-writes lag.
        refreshed = tenants.update(tenant_id, {"stripe_customer_id": None})
        customer_id = _ensure_stripe_customer(refreshed, email)
        url = stripe_client.create_checkout_session(
            tenant_id=tenant_id,
            customer_id=customer_id,
            recurring_price_id=prices.recurring,
            setup_price_id=prices.setup,
            success_url=success_url,
            cancel_url=cancel_url,
        )

    log.info("billing_checkout_created", tenant_id=tenant_id, plan=plan)
    return url


def create_portal_session(*, tenant_id: str, return_url: str) -> str:
    """Open the Stripe-hosted Customer Portal for this tenant.

    Requires a Stripe customer id on the tenant (created at bootstrap, or
    backfilled during the first checkout). We don't create one on the fly here:
    a tenant with no Stripe customer has nothing to manage in the portal.
    """
    if not stripe_client.is_configured():
        raise BillingNotConfiguredError(
            "Stripe is not configured on this environment",
            detail={"reason": "no_stripe_key"},
        )

    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    customer_id = tenant.get("stripe_customer_id")
    if not customer_id:
        raise NoCustomerError(
            "Tenant has no Stripe customer attached; start a checkout first.",
            detail={"tenant_id": tenant_id},
        )

    url = stripe_client.create_billing_portal_session(
        customer_id=str(customer_id),
        return_url=return_url,
    )
    log.info("billing_portal_created", tenant_id=tenant_id)
    return url


def _iso_from_epoch(ts: Any) -> str | None:
    """Stripe returns Unix timestamps; the UI wants ISO strings."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).isoformat()
    except (TypeError, ValueError):
        return None


def get_subscription_summary(tenant_id: str) -> SubscriptionSummary:
    """Snapshot of billing state for the dashboard.

    DB is the source of truth for plan/is_active (kept in sync by webhooks).
    Stripe is queried lazily for the period end + cancel_at_period_end so we
    don't have to mirror those into our schema. Stripe failures degrade
    gracefully — the page still renders with DB-only fields.
    """
    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    subscription_id = tenant.get("stripe_subscription_id")
    summary = SubscriptionSummary(
        plan=tenant["plan"],
        is_active=bool(tenant.get("is_active", False)),
        is_founding_member=bool(tenant.get("is_founding_member", False)),
        trial_ends_at=tenant.get("trial_ends_at"),
        cancelled_at=tenant.get("cancelled_at"),
        has_subscription=bool(subscription_id),
        trial_status=compute_trial_status(tenant),
    )

    if not subscription_id:
        return summary

    try:
        sub = stripe_client.retrieve_subscription(str(subscription_id))
    except Exception as exc:
        # Don't 500 the dashboard if Stripe is flaky. Log and return what we
        # have; the next page load (or webhook) will recover the missing bits.
        log.warning(
            "billing_subscription_fetch_failed",
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            error=str(exc),
        )
        return summary

    if sub is None:
        # Subscription id we stored no longer exists in Stripe (env switch,
        # manual delete). Keep summary minimal; webhook will eventually fire
        # `customer.subscription.deleted` and we'll deactivate properly.
        return summary

    summary.status = sub.get("status")
    summary.current_period_end = _iso_from_epoch(sub.get("current_period_end"))
    summary.cancel_at_period_end = bool(sub.get("cancel_at_period_end"))
    return summary
