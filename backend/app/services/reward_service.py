from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from app.db import rewards
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
    if reward["redeemed_at"] is not None:
        raise AlreadyRedeemedError("Reward already redeemed")
    expires_at = datetime.fromisoformat(reward["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(UTC):
        raise ExpiredError("Reward has expired")

    redeemed = rewards.redeem(reward_id, redeemed_by_user)
    log.info("reward_redeemed", reward_id=reward_id, redeemed_by_user=redeemed_by_user)
    return RedeemResult(
        reward_id=redeemed["id"],
        redeemed_at=redeemed["redeemed_at"],
        description=redeemed["description"],
    )
