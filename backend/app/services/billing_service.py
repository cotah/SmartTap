from dataclasses import dataclass
from typing import Literal

import structlog

from app.config import get_settings
from app.db import tenants
from app.errors import BusinessError, NotFoundError
from app.services import stripe_client

log = structlog.get_logger(__name__)

BillingPlan = Literal["review", "loyalty", "pro", "network"]


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
