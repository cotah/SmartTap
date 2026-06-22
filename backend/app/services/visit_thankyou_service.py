"""Post-visit thank-you — the real-time email that fires the moment a tap
earns a stamp.

Sibling in spirit to `review_nudge_service`, but with one defining difference:
this is NOT a daily cron. The send is triggered synchronously off a single tap
via FastAPI BackgroundTasks (see `routers/taps.py`), so the customer-facing
`/t/[uuid]` page never waits on Resend. This module owns the *policy* for that
single customer; it does NOT own HTTP concerns and never raises into the tap
request.

Policy (hardcoded for v1, matching how reactivation/review_nudge started):
    THANKYOU_ENABLED   → global kill-switch (config) — the master off lever
    stamp_awarded      → only when this tap actually moved the card
    gdpr_consent       → never email a customer who didn't opt in
    email present      → nothing to send to otherwise
    magic_link_token   → needed for the opt-out link (+ the stamp-card fallback)
    COOLDOWN_HOURS = 6 → dedupe: tap twice in a visit, or return the same day,
                         and you still get at most one thank-you

This collapses the two rules Henrique asked for — "once per visit" and "not
within 6 hours" — into one short cooldown: a rapid re-tap doesn't even earn a
stamp (the stamp rate-limit in tap_service blocks it), and a genuine same-day
return is caught by the 6h window.

Failure & idempotency mirror the cron flows: mark the cooldown BEFORE the send,
swallow errors. A crash after the mark costs the customer one thank-you, never
a duplicate.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import structlog

from app.config import get_settings
from app.db import customers
from app.services import email_service

log = structlog.get_logger(__name__)


COOLDOWN_HOURS = 6


# A small, testable verdict for each call. The status strings double as the
# reason a thank-you was (or wasn't) sent — handy in logs and unit tests.
ThankyouStatus = Literal[
    "sent",
    "skipped_disabled",
    "skipped_no_stamp",
    "skipped_no_consent",
    "skipped_no_email",
    "skipped_no_token",
    "skipped_cooldown",
    "error",
]


@dataclass
class ThankyouResult:
    status: ThankyouStatus
    customer_id: str | None = None


def _opt_out_url(magic_link_token: str) -> str:
    """Reuses the shared customer opt-out route (`/u/<token>`). Revoking consent
    there flips gdpr_consent=false, which silences reactivation, review-nudge
    AND this thank-you — one opt-out covers all merchant-to-customer email."""
    base = get_settings().site_url.rstrip("/")
    return f"{base}/u/{magic_link_token}"


def _magic_link_url(magic_link_token: str) -> str:
    """The customer's own stamp card (`/m/<token>`), same shape reactivation
    uses for its "show my stamps" CTA. Used as the thank-you CTA when the
    tenant has no Google review URL configured."""
    base = get_settings().site_url.rstrip("/")
    return f"{base}/m/{magic_link_token}"


def _parse_ts(value: Any) -> datetime | None:
    """Parse a Supabase timestamp into an aware UTC datetime; None if missing
    or unparseable (a bad value must never block a send by looking 'recent')."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def maybe_send(
    *,
    tenant: dict[str, Any],
    customer: dict[str, Any],
    stamp_awarded: bool,
    now: datetime | None = None,
) -> ThankyouResult:
    """Decide and (best-effort) send the thank-you for one tap.

    Called from a BackgroundTask after the tap response is already on the wire,
    so it returns a ThankyouResult instead of raising — the tap has long since
    succeeded. `now` is injectable for tests.

    The `customer` row is the post-tap snapshot from `process_tap` (it already
    reflects the awarded stamp and carries `last_thankyou_sent_at`), so the
    cooldown check needs no extra read.
    """
    current = now or datetime.now(UTC)
    cid = customer.get("id") if isinstance(customer.get("id"), str) else None

    if not get_settings().thankyou_enabled:
        return ThankyouResult("skipped_disabled", cid)

    if not stamp_awarded:
        # No stamp moved → not a "you earned a stamp" moment. (Rapid re-taps
        # that the stamp rate-limit blocked land here, which is what dedupes
        # double-taps within a visit.)
        return ThankyouResult("skipped_no_stamp", cid)

    if not customer.get("gdpr_consent"):
        return ThankyouResult("skipped_no_consent", cid)

    email = (customer.get("email") or "").strip()
    if not email:
        return ThankyouResult("skipped_no_email", cid)

    token = customer.get("magic_link_token")
    if not isinstance(token, str) or not token:
        # Without a token we can't render a working opt-out link — skip rather
        # than send an email the customer can't unsubscribe from.
        return ThankyouResult("skipped_no_token", cid)

    last_sent = _parse_ts(customer.get("last_thankyou_sent_at"))
    if last_sent is not None and last_sent > current - timedelta(hours=COOLDOWN_HOURS):
        return ThankyouResult("skipped_cooldown", cid)

    if not isinstance(cid, str):
        # Belt-and-suspenders: everything above passed but we somehow have no
        # id to mark the cooldown against. Don't send what we can't dedupe.
        return ThankyouResult("error", None)

    review_url = (tenant.get("google_review_url") or "").strip() or None

    try:
        # Mark FIRST (mark-before-send): a failure in the send path then costs
        # this customer one thank-you, never a duplicate on a retried tap.
        customers.mark_thankyou_sent(cid, current)
        email_service.send_visit_thankyou(
            tenant=tenant,
            customer=customer,
            review_url=review_url,
            magic_link_url=_magic_link_url(token),
            opt_out_url=_opt_out_url(token),
        )
    except Exception as exc:
        # Never propagate — the tap already returned. email_service swallows
        # Resend errors itself; this guards the DB mark and URL building too.
        log.exception(
            "visit_thankyou_failed",
            tenant_id=tenant.get("id"),
            customer_id=cid,
            error=str(exc),
        )
        return ThankyouResult("error", cid)

    log.info(
        "visit_thankyou_sent",
        tenant_id=tenant.get("id"),
        customer_id=cid,
        had_review_url=review_url is not None,
    )
    return ThankyouResult("sent", cid)
