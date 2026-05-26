import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.db import customers, nfc_tags, rewards, stamps, taps, tenants
from app.errors import InactiveError, NotFoundError
from app.services import campaign_service
from app.services.stamp_engine import (
    can_award_stamp,
    generate_validation_code,
    multiplier_for_campaign,
    reward_expiry,
)

log = structlog.get_logger(__name__)

Row = dict[str, Any]


@dataclass(frozen=True)
class TapContext:
    tag_uuid: str
    device_type: str
    interaction_type: str
    magic_link_token: str | None
    user_agent: str | None
    ip: str | None


@dataclass
class TapResult:
    tenant: Row
    customer: Row | None
    stamps_current: int
    reward_available: Row | None
    tap_id: str
    stamp_awarded: bool
    # Active double_stamp campaign at the moment of this tap, or None. Used
    # by the customer-facing page to render a "2x today" badge.
    active_campaign: Row | None = None
    # How many stamps this tap actually awarded (1 normally; 2..5 during a
    # double_stamp campaign). Surfaced so the UI can say "+2 stamps" instead
    # of always showing "+1".
    stamps_awarded_count: int = 0


def _hash_ip(ip: str | None) -> str | None:
    if ip is None:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def process_tap(ctx: TapContext) -> TapResult:
    tag = nfc_tags.get_by_tag_uuid(ctx.tag_uuid)
    if tag is None:
        raise NotFoundError("Tag not found", detail={"tag_uuid": ctx.tag_uuid})
    if not tag["is_active"]:
        raise InactiveError("Tag is no longer active")

    tenant = tenants.get_by_id(tag["tenant_id"])
    if tenant is None:
        raise NotFoundError("Tenant not found")
    if not tenant["is_active"]:
        raise InactiveError("Tenant is no longer active")

    customer: Row | None = None
    if ctx.magic_link_token:
        customer = customers.get_by_magic_token(ctx.magic_link_token)
        if customer is not None and customer["tenant_id"] != tenant["id"]:
            customer = None

    tap = taps.create(
        tag_id=tag["id"],
        tenant_id=tenant["id"],
        customer_id=customer["id"] if customer else None,
        device_type=ctx.device_type,
        interaction_type=ctx.interaction_type,
        user_agent=ctx.user_agent,
        ip_hash=_hash_ip(ctx.ip),
    )

    stamp_awarded = False
    reward_available: Row | None = None
    awarded_count = 0

    # Look up the active double_stamp campaign once per tap. None when no
    # campaign is live — the common path. Lookup is cheap (partial index).
    now = datetime.now(UTC)
    active_campaign = campaign_service.find_active_for_tap(tenant["id"], now=now)
    multiplier = multiplier_for_campaign(active_campaign)

    if customer is not None:
        last_stamp = stamps.last_for_customer(customer["id"])
        last_at = _parse_iso(last_stamp["created_at"]) if last_stamp else None
        if can_award_stamp(last_at, tenant["stamp_rate_limit_minutes"], now):
            # Single stamp row per tap, but its multiplier captures campaign
            # weight. current_stamps moves by `multiplier`, so the customer's
            # card visibly jumps 2 (or N) during a double_stamp window.
            stamps.create(
                customer_id=customer["id"],
                tenant_id=tenant["id"],
                tap_id=tap["id"],
                multiplier=multiplier,
            )
            stamp_awarded = True
            awarded_count = multiplier
            updated = customers.update(
                customer["id"],
                {
                    "current_stamps": customer["current_stamps"] + multiplier,
                    "total_stamps": customer["total_stamps"] + multiplier,
                    "total_visits": customer["total_visits"] + 1,
                    "last_visit_at": now.isoformat(),
                },
            )
            customer = updated

            if customer["current_stamps"] >= tenant["stamps_for_reward"]:
                new_reward = rewards.create(
                    customer_id=customer["id"],
                    tenant_id=tenant["id"],
                    stamps_used=tenant["stamps_for_reward"],
                    description=tenant["reward_description"] or "Free reward",
                    validation_code=generate_validation_code(),
                    expires_at=reward_expiry(
                        now, tenant["reward_expires_days"]
                    ).isoformat(),
                )
                # Reset to the *remainder* so a double_stamp tap that pushes
                # past the threshold doesn't waste extra stamps. Example:
                # current=9, multiplier=2, threshold=10 → reward + 1 left.
                remainder = customer["current_stamps"] - tenant["stamps_for_reward"]
                customer = customers.update(
                    customer["id"],
                    {"current_stamps": max(0, remainder)},
                )
                reward_available = new_reward

        if reward_available is None:
            reward_available = rewards.get_active_for_customer(customer["id"])

    log.info(
        "tap_processed",
        tenant_id=tenant["id"],
        tag_id=tag["id"],
        customer_identified=customer is not None,
        stamp_awarded=stamp_awarded,
        stamps_awarded_count=awarded_count,
        reward_available=reward_available is not None,
        campaign_id=active_campaign["id"] if active_campaign else None,
    )

    return TapResult(
        tenant=tenant,
        customer=customer,
        stamps_current=customer["current_stamps"] if customer else 0,
        reward_available=reward_available,
        tap_id=tap["id"],
        stamp_awarded=stamp_awarded,
        active_campaign=active_campaign,
        stamps_awarded_count=awarded_count,
    )
