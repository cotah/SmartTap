"""Orchestration layer for transactional emails.

Each public function answers a higher-level business event ("welcome a new
tenant", "payment succeeded for tenant X") and is responsible for:

    1. Resolving the recipient email (best-effort, never raises)
    2. Rendering the right template
    3. Calling resend_client.send and catching errors

Emails are intentionally NOT critical path. A Resend outage must never roll
back a webhook or fail a signup — we log, push to Sentry, and move on. The
caller can assume these functions always return cleanly.
"""

from typing import Any

import structlog

from app.db import tenant_members, users
from app.emails import templates
from app.services import resend_client

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_send(
    *,
    to: str | None,
    rendered: templates.RenderedEmail,
    tenant_id: str | None,
    event_name: str,
    tags: list[dict[str, str]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    """Common send path with full error containment.

    `event_name` is a short stable label for log correlation ("welcome",
    "payment_succeeded") and doubles as a Resend tag for dashboard filtering.
    The kwarg is named `event_name` (not `event`) because structlog reserves
    the keyword `event` for the log message itself.
    """
    if not to:
        log.info("email_skip_no_recipient", event_name=event_name, tenant_id=tenant_id)
        return

    if not resend_client.is_configured():
        # Dev / CI without RESEND_API_KEY. No-op silently — this is normal.
        log.info(
            "email_skip_resend_unconfigured",
            event_name=event_name,
            tenant_id=tenant_id,
        )
        return

    full_tags = [{"name": "event", "value": event_name}]
    if tags:
        full_tags.extend(tags)

    try:
        resend_client.send(
            to=to,
            subject=rendered.subject,
            html=rendered.html,
            text=rendered.text,
            tags=full_tags,
            attachments=attachments,
        )
    except Exception as exc:
        # Sentry will pick this up via structlog → its integration; we don't
        # raise because the surrounding business operation (signup, webhook)
        # must succeed regardless of email deliverability.
        log.exception(
            "email_send_failed",
            event_name=event_name,
            tenant_id=tenant_id,
            error=str(exc),
        )


def _owner_email(tenant_id: str) -> str | None:
    """Resolve the owner's email for a tenant. Two lookups (member → user);
    both can return None and we degrade silently."""
    user_id = tenant_members.get_owner_user_id(tenant_id)
    if not user_id:
        return None
    return users.get_email_by_user_id(user_id)


# ---------------------------------------------------------------------------
# Public API — one function per business event
# ---------------------------------------------------------------------------


def send_welcome(*, tenant: dict[str, Any], email: str | None) -> None:
    """Sent once when bootstrap creates a brand-new tenant. The email arg is
    optional because callers (bootstrap_owner) already have it from the JWT;
    skip the auth lookup roundtrip when we can."""
    rendered = templates.welcome_email(tenant=tenant)
    _safe_send(
        to=email,
        rendered=rendered,
        tenant_id=tenant.get("id"),
        event_name="welcome",
    )


def send_payment_succeeded(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    session: dict[str, Any],
) -> None:
    """Sent from the checkout.session.completed webhook. Uses the session's
    amount_total + currency for the confirmation line."""
    rendered = templates.payment_succeeded_email(
        tenant=tenant,
        plan=tenant.get("plan"),
        amount_total=session.get("amount_total"),
        currency=str(session.get("currency") or "eur"),
    )
    _safe_send(
        to=_owner_email(tenant_id),
        rendered=rendered,
        tenant_id=tenant_id,
        event_name="payment_succeeded",
    )


def send_payment_failed(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    invoice: dict[str, Any],
) -> None:
    """Sent from the invoice.payment_failed webhook. Stripe re-tries
    automatically; this email nudges the user to update payment ahead of
    that retry exhausting."""
    rendered = templates.payment_failed_email(
        tenant=tenant,
        amount_due=invoice.get("amount_due"),
        currency=str(invoice.get("currency") or "eur"),
    )
    _safe_send(
        to=_owner_email(tenant_id),
        rendered=rendered,
        tenant_id=tenant_id,
        event_name="payment_failed",
    )


def send_subscription_canceled(*, tenant_id: str, tenant: dict[str, Any]) -> None:
    """Sent from customer.subscription.deleted. Confirmation, not a save-attempt
    — by the time this fires, the user already decided to cancel."""
    rendered = templates.subscription_canceled_email(tenant=tenant)
    _safe_send(
        to=_owner_email(tenant_id),
        rendered=rendered,
        tenant_id=tenant_id,
        event_name="subscription_canceled",
    )


def send_monthly_report(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    year: int,
    month: int,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> None:
    """Sent on the 1st of each Dublin month with the previous month's PDF.

    The recipient is the tenant OWNER (not end customers). Attaches the PDF
    rather than linking to a download — merchants tend to forward these to
    their accountant or save them locally, and a link would 404 once the
    month rolled forward (the PDF is generated on-demand, never persisted).
    """
    rendered = templates.monthly_report_email(
        tenant=tenant, year=year, month=month
    )
    attachment = resend_client.build_pdf_attachment(
        filename=pdf_filename, pdf_bytes=pdf_bytes
    )
    _safe_send(
        to=_owner_email(tenant_id),
        rendered=rendered,
        tenant_id=tenant_id,
        event_name="monthly_report",
        tags=[{"name": "period", "value": f"{year:04d}-{month:02d}"}],
        attachments=[attachment],
    )


def send_reactivation(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    magic_link_url: str,
    opt_out_url: str,
) -> bool:
    """Sent by the daily cron to a dormant customer of this tenant.

    Unlike the merchant-facing emails above, the recipient is the END CUSTOMER
    (not the tenant owner). The address comes off the customer row — we trust
    the caller (reactivation_service) to have already filtered out customers
    without an email or without GDPR consent.

    Returns True when a send was actually attempted (or no-op'd cleanly in dev),
    False when the customer had no email and we skipped. The caller uses this
    to decide whether to record the cooldown.
    """
    to = (customer.get("email") or "").strip() or None
    if not to:
        # Belt-and-suspenders — DB query already filters, but if a caller ever
        # invokes this directly we don't want a confusing crash.
        log.info(
            "reactivation_skip_no_email",
            tenant_id=tenant.get("id"),
            customer_id=customer.get("id"),
        )
        return False

    rendered = templates.reactivation_email(
        tenant=tenant,
        customer=customer,
        magic_link_url=magic_link_url,
        opt_out_url=opt_out_url,
    )
    _safe_send(
        to=to,
        rendered=rendered,
        tenant_id=tenant.get("id"),
        event_name="reactivation",
        tags=[{"name": "tenant_id", "value": str(tenant.get("id") or "unknown")}],
    )
    return True
