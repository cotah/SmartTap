from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.db import customers, rewards
from app.errors import (
    AlreadyRedeemedError,
    ExpiredError,
    InvalidCodeError,
    NotFoundError,
)

log = structlog.get_logger(__name__)

Row = dict[str, Any]


@dataclass
class RedeemResult:
    reward_id: str
    redeemed_at: str
    description: str
    customer_id: str
    customer_name: str | None


def _redeem_checked(reward: Row, redeemed_by_user: str | None) -> RedeemResult:
    if reward["redeemed_at"] is not None:
        raise AlreadyRedeemedError("Reward already redeemed")
    expires_at = datetime.fromisoformat(reward["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(UTC):
        raise ExpiredError("Reward has expired")

    redeemed = rewards.redeem(reward["id"], redeemed_by_user)
    customer = customers.get_by_id(reward["customer_id"])
    log.info(
        "reward_redeemed",
        reward_id=reward["id"],
        redeemed_by_user=redeemed_by_user,
    )
    return RedeemResult(
        reward_id=redeemed["id"],
        redeemed_at=redeemed["redeemed_at"],
        description=redeemed["description"],
        customer_id=reward["customer_id"],
        customer_name=customer.get("name") if customer else None,
    )


def validate_and_redeem(
    *,
    reward_id: str,
    validation_code: str,
    redeemed_by_user: str | None,
) -> RedeemResult:
    reward = rewards.get_by_id(reward_id)
    if reward is None:
        raise NotFoundError("Reward not found", detail={"reward_id": reward_id})
    if reward["validation_code"] != validation_code:
        raise InvalidCodeError("Validation code does not match")
    return _redeem_checked(reward, redeemed_by_user)


def validate_and_redeem_by_code(
    *,
    tenant_id: str,
    validation_code: str,
    redeemed_by_user: str | None,
) -> RedeemResult:
    """Staff-facing redeem: looks the reward up by code inside the caller's tenant.

    Tenant scoping is enforced at the DB lookup, so codes from other tenants
    cannot be redeemed even if they collide.
    """
    reward = rewards.get_by_validation_code(tenant_id, validation_code)
    if reward is None:
        raise InvalidCodeError("No reward matches that code")
    return _redeem_checked(reward, redeemed_by_user)
