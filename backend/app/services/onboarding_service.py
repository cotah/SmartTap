import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.db import tenant_members, tenants
from app.services import email_service, stripe_client

log = structlog.get_logger(__name__)

Row = dict[str, Any]

TRIAL_DAYS = 30


@dataclass
class BootstrapResult:
    tenant: Row
    is_new: bool


def _slug_from_email(email: str | None) -> str:
    if not email:
        return "owner"
    local = email.split("@")[0]
    cleaned = re.sub(r"[^a-z0-9-]+", "-", local.lower()).strip("-")
    return cleaned or "owner"


def _unique_slug(base: str) -> str:
    if tenants.get_by_slug(base) is None:
        return base
    for _ in range(8):
        candidate = f"{base}-{secrets.token_hex(2)}"
        if tenants.get_by_slug(candidate) is None:
            return candidate
    raise RuntimeError("could not generate unique slug")


def bootstrap_owner(
    *,
    user_id: str,
    email: str | None,
    business_name: str | None = None,
) -> BootstrapResult:
    existing_members = tenant_members.list_for_user(user_id)
    if existing_members:
        tenant = tenants.get_by_id(existing_members[0]["tenant_id"])
        if tenant is None:
            raise RuntimeError("tenant_member points to missing tenant")
        log.info("bootstrap_existing", user_id=user_id, tenant_id=tenant["id"])
        return BootstrapResult(tenant=tenant, is_new=False)

    slug = _unique_slug(_slug_from_email(email))
    trial_ends = datetime.now(UTC) + timedelta(days=TRIAL_DAYS)

    tenant = tenants.create(
        {
            "slug": slug,
            "name": business_name or "My business",
            "business_type": "other",
            "plan": "trial",
            "trial_ends_at": trial_ends.isoformat(),
        }
    )
    tenant_members.create(tenant_id=tenant["id"], user_id=user_id, role="owner")
    log.info("bootstrap_created", user_id=user_id, tenant_id=tenant["id"], slug=slug)

    # Best-effort: attach a Stripe Customer so the upgrade flow (S3-W2) can
    # use it later. If this fails (or Stripe is not configured) the tenant
    # stays usable; we'll backfill via webhook/retry. Idempotency on the
    # Stripe side prevents duplicates if bootstrap retries.
    tenant = _attach_stripe_customer(tenant, email)

    # Welcome email is best-effort and only fires on first creation. The
    # `existing_members` branch above returns early without reaching here,
    # so retries of bootstrap (e.g. transient client errors) never duplicate
    # the welcome email — the second call sees a member and returns is_new=False.
    email_service.send_welcome(tenant=tenant, email=email)

    return BootstrapResult(tenant=tenant, is_new=True)


def _attach_stripe_customer(tenant: Row, email: str | None) -> Row:
    try:
        stripe_customer_id = stripe_client.create_customer(
            tenant_id=tenant["id"],
            email=email,
            name=tenant["name"],
        )
    except Exception as exc:  # pragma: no cover - network failure path
        log.warning(
            "stripe_create_customer_failed",
            tenant_id=tenant["id"],
            error=str(exc),
        )
        return tenant

    if stripe_customer_id is None:
        return tenant

    try:
        return tenants.update(tenant["id"], {"stripe_customer_id": stripe_customer_id})
    except Exception as exc:  # pragma: no cover - DB failure path
        log.error(
            "stripe_customer_id_persist_failed",
            tenant_id=tenant["id"],
            stripe_customer_id=stripe_customer_id,
            error=str(exc),
        )
        return tenant


VALID_BUSINESS_TYPES = frozenset(
    ["barbershop", "cafe", "pet_grooming", "salon", "tattoo", "other"]
)


@dataclass(frozen=True)
class OnboardingPayload:
    business_name: str
    business_type: str
    google_review_url: str | None
    stamps_for_reward: int
    reward_description: str
    reward_expires_days: int
    stamp_rate_limit_minutes: int


def complete_onboarding(tenant_id: str, payload: OnboardingPayload) -> Row:
    """Atomic completion of the post-signup wizard.

    All wizard fields land in a single DB update so we never end up with a
    half-onboarded tenant if a request times out mid-way.
    """
    from app.errors import NotFoundError

    if payload.business_type not in VALID_BUSINESS_TYPES:
        raise ValueError(f"invalid business_type: {payload.business_type}")

    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    fields: dict[str, Any] = {
        "name": payload.business_name.strip(),
        "business_type": payload.business_type,
        "stamps_for_reward": payload.stamps_for_reward,
        "reward_description": payload.reward_description.strip(),
        "reward_expires_days": payload.reward_expires_days,
        "stamp_rate_limit_minutes": payload.stamp_rate_limit_minutes,
        "google_review_url": (payload.google_review_url or "").strip() or None,
    }
    updated = tenants.update(tenant_id, fields)
    log.info(
        "onboarding_completed",
        tenant_id=tenant_id,
        business_type=payload.business_type,
    )
    return updated
