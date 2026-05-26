"""Dispatcher and handlers for Stripe webhook events.

Design notes
------------
* Idempotency is enforced at the entrypoint (`handle`) by `stripe_events.claim`.
  Handlers themselves assume they run exactly once per event.
* Handlers raise on infrastructure failures (DB unreachable, bug) so the
  caller can return 5xx and Stripe retries. They DO NOT raise on "expected"
  data issues (unknown tenant, unknown price); those are logged and swallowed
  because retrying won't help and we don't want Stripe stuck on a bad event.
* The single source of truth for plan/state changes is the
  `customer.subscription.*` family. `checkout.session.completed` only links the
  subscription to the tenant; `invoice.*` events are observability only.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from app.config import get_settings
from app.db import stripe_events, tenants
from app.services import email_service

log = structlog.get_logger(__name__)

BillingPlan = Literal["review", "loyalty", "pro", "network"]

# Subscription statuses Stripe sends in `customer.subscription.updated`.
# https://stripe.com/docs/api/subscriptions/object#subscription_object-status
_ACTIVE_STATUSES = frozenset({"active", "trialing"})
_CANCELED_STATUSES = frozenset({"canceled"})
_AT_RISK_STATUSES = frozenset({"past_due", "unpaid"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plan_from_price_id(price_id: str | None) -> BillingPlan | None:
    """Reverse-lookup a Stripe price_id to one of our four plan names.

    Built from settings on every call (cheap dict build) so test monkeypatches
    of get_settings take effect without restarting a module-level cache.
    """
    if not price_id:
        return None
    s = get_settings()
    lookup: dict[str, BillingPlan] = {}
    for plan_name, price in (
        ("review", s.stripe_price_review),
        ("loyalty", s.stripe_price_loyalty),
        ("pro", s.stripe_price_pro),
        ("network", s.stripe_price_network),
    ):
        if price:
            lookup[price] = plan_name  # type: ignore[assignment]
    return lookup.get(price_id)


def _resolve_tenant_id(
    *,
    metadata_tenant_id: str | None,
    stripe_subscription_id: str | None,
    stripe_customer_id: str | None,
) -> str | None:
    """Try metadata first (cheapest, no DB hit), fall back to DB lookups.

    Stripe events created by our checkout flow always carry tenant_id in
    metadata, but events triggered manually in the dashboard (refund, cancel,
    plan change) may not. Falling back to subscription_id then customer_id
    keeps us resilient to ops actions.
    """
    if metadata_tenant_id:
        return metadata_tenant_id
    if stripe_subscription_id:
        row = tenants.get_by_stripe_subscription(stripe_subscription_id)
        if row:
            return str(row["id"])
    if stripe_customer_id:
        row = tenants.get_by_stripe_customer(stripe_customer_id)
        if row:
            return str(row["id"])
    return None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _first_price_id(subscription: dict[str, Any]) -> str | None:
    """Subscriptions always have at least one item; grab the recurring one.
    The setup fee is a separate one-time invoice line, so on the subscription
    object we expect a single recurring item."""
    items = (subscription.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    pid = price.get("id")
    return str(pid) if pid else None


# ---------------------------------------------------------------------------
# Per-event handlers
# ---------------------------------------------------------------------------


def _on_checkout_completed(session: dict[str, Any]) -> None:
    """First step in the activation flow. Links the Stripe Subscription to the
    tenant and flips is_active. Plan + status will be set by the
    `customer.subscription.updated` event Stripe fires immediately after."""
    metadata = session.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    resolved_tenant = _resolve_tenant_id(
        metadata_tenant_id=tenant_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not resolved_tenant:
        log.warning(
            "stripe_checkout_completed_no_tenant",
            session_id=session.get("id"),
            customer_id=customer_id,
        )
        return
    if not subscription_id:
        # Non-subscription checkout (shouldn't happen with our flow, but guard
        # so we don't write garbage).
        log.warning(
            "stripe_checkout_completed_no_subscription",
            tenant_id=resolved_tenant,
            session_id=session.get("id"),
        )
        return

    tenants.update(
        resolved_tenant,
        {
            "stripe_subscription_id": str(subscription_id),
            "is_active": True,
            "cancelled_at": None,
        },
    )
    log.info(
        "stripe_checkout_completed_applied",
        tenant_id=resolved_tenant,
        subscription_id=subscription_id,
    )

    # Confirmation email. Re-fetch the tenant so the email uses the freshly
    # written values (esp. is_active) — webhook idempotency means this fires
    # exactly once per checkout. Best-effort: email failures don't 5xx.
    updated_tenant = tenants.get_by_id(resolved_tenant)
    if updated_tenant is not None:
        email_service.send_payment_succeeded(
            tenant_id=resolved_tenant,
            tenant=updated_tenant,
            session=session,
        )


def _on_subscription_updated(subscription: dict[str, Any]) -> None:
    """Authoritative source of plan + status. Runs on every change: trial→active,
    plan switch, payment past_due, dashboard cancel-at-period-end, etc."""
    metadata = subscription.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    subscription_id = subscription.get("id")
    customer_id = subscription.get("customer")

    resolved_tenant = _resolve_tenant_id(
        metadata_tenant_id=tenant_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not resolved_tenant:
        log.warning(
            "stripe_subscription_updated_no_tenant",
            subscription_id=subscription_id,
            customer_id=customer_id,
        )
        return

    status = subscription.get("status")
    price_id = _first_price_id(subscription)
    plan = _plan_from_price_id(price_id)

    update: dict[str, Any] = {
        "stripe_subscription_id": str(subscription_id) if subscription_id else None,
    }

    if status in _ACTIVE_STATUSES:
        update["is_active"] = True
        update["cancelled_at"] = None
        if plan is not None:
            update["plan"] = plan
        else:
            # Unknown price → don't touch plan, but still keep tenant active.
            # Operator can investigate; logging gives us the price_id to map.
            log.warning(
                "stripe_subscription_unknown_price",
                tenant_id=resolved_tenant,
                price_id=price_id,
                subscription_id=subscription_id,
            )
    elif status in _CANCELED_STATUSES:
        update["is_active"] = False
        update["cancelled_at"] = _now_iso()
        # Plan retained on purpose (decision #3): history + frictionless reactivation.
    elif status in _AT_RISK_STATUSES:
        # Stripe is still retrying payment; don't deactivate yet. Just log so
        # we can wire dunning emails later. If retries exhaust, Stripe will
        # send subscription.deleted (or canceled) and we deactivate then.
        log.warning(
            "stripe_subscription_at_risk",
            tenant_id=resolved_tenant,
            status=status,
            subscription_id=subscription_id,
        )
    else:
        # incomplete, incomplete_expired, paused — record id but don't mutate
        # is_active/plan; let the next definitive event drive state.
        log.info(
            "stripe_subscription_neutral_status",
            tenant_id=resolved_tenant,
            status=status,
            subscription_id=subscription_id,
        )

    tenants.update(resolved_tenant, update)
    log.info(
        "stripe_subscription_updated_applied",
        tenant_id=resolved_tenant,
        status=status,
        plan=plan,
    )


def _on_subscription_deleted(subscription: dict[str, Any]) -> None:
    """Subscription ended for real (not just scheduled). Deactivate the tenant
    but preserve historical plan + subscription_id for support/reactivation."""
    metadata = subscription.get("metadata") or {}
    tenant_id = metadata.get("tenant_id")
    subscription_id = subscription.get("id")
    customer_id = subscription.get("customer")

    resolved_tenant = _resolve_tenant_id(
        metadata_tenant_id=tenant_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not resolved_tenant:
        log.warning(
            "stripe_subscription_deleted_no_tenant",
            subscription_id=subscription_id,
            customer_id=customer_id,
        )
        return

    tenants.update(
        resolved_tenant,
        {"is_active": False, "cancelled_at": _now_iso()},
    )
    log.info(
        "stripe_subscription_deleted_applied",
        tenant_id=resolved_tenant,
        subscription_id=subscription_id,
    )

    updated_tenant = tenants.get_by_id(resolved_tenant)
    if updated_tenant is not None:
        email_service.send_subscription_canceled(
            tenant_id=resolved_tenant,
            tenant=updated_tenant,
        )


def _on_invoice_payment_succeeded(invoice: dict[str, Any]) -> None:
    """Observability only. Subscription.updated drives state; logging here lets
    us correlate revenue events with the tenant in Sentry/structlog."""
    log.info(
        "stripe_invoice_paid",
        invoice_id=invoice.get("id"),
        customer_id=invoice.get("customer"),
        amount_paid=invoice.get("amount_paid"),
        subscription_id=invoice.get("subscription"),
    )


def _on_invoice_payment_failed(invoice: dict[str, Any]) -> None:
    """Nudge the owner to update their payment method. The actual state
    change (is_active flip) comes from subscription.updated(status=past_due),
    which is where the dashboard banner is driven from — this email is just
    a heads-up while Stripe still has retries left."""
    log.warning(
        "stripe_invoice_failed",
        invoice_id=invoice.get("id"),
        customer_id=invoice.get("customer"),
        amount_due=invoice.get("amount_due"),
        subscription_id=invoice.get("subscription"),
        attempt_count=invoice.get("attempt_count"),
    )

    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    resolved_tenant = _resolve_tenant_id(
        metadata_tenant_id=None,  # invoices don't carry our metadata
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )
    if not resolved_tenant:
        return
    tenant = tenants.get_by_id(resolved_tenant)
    if tenant is None:
        return
    email_service.send_payment_failed(
        tenant_id=resolved_tenant,
        tenant=tenant,
        invoice=invoice,
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict[str, Any]], None]

_HANDLERS: dict[str, HandlerFn] = {
    "checkout.session.completed": _on_checkout_completed,
    "customer.subscription.updated": _on_subscription_updated,
    "customer.subscription.created": _on_subscription_updated,  # same shape, same logic
    "customer.subscription.deleted": _on_subscription_deleted,
    "invoice.payment_succeeded": _on_invoice_payment_succeeded,
    "invoice.payment_failed": _on_invoice_payment_failed,
}


def handle(event: dict[str, Any]) -> None:
    """Entrypoint called by the webhook router.

    Idempotency: the first call for a given event_id records it and runs the
    handler; subsequent calls find the event in the table and short-circuit.
    """
    event_id = event["id"]
    event_type = event["type"]

    if not stripe_events.claim(event_id, event_type, event):
        log.info("stripe_event_already_processed", event_id=event_id, type=event_type)
        return

    handler = _HANDLERS.get(event_type)
    if handler is None:
        # Unhandled event type — claimed (so retries don't re-process) but
        # there's nothing to do. We deliberately subscribe in the Stripe
        # dashboard only to types we handle, so this is mostly defensive.
        log.info("stripe_event_unhandled", event_id=event_id, type=event_type)
        return

    obj = (event.get("data") or {}).get("object") or {}
    handler(obj)
