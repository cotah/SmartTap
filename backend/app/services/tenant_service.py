from dataclasses import dataclass
from typing import Any

import structlog

from app.db import tenants
from app.errors import NotFoundError

log = structlog.get_logger(__name__)

Row = dict[str, Any]


@dataclass(frozen=True)
class RewardConfig:
    stamps_for_reward: int
    reward_description: str
    reward_expires_days: int
    stamp_rate_limit_minutes: int


def get_self(tenant_id: str) -> Row:
    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})
    return tenant


def update_reward_config(tenant_id: str, config: RewardConfig) -> Row:
    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    updated = tenants.update(
        tenant_id,
        {
            "stamps_for_reward": config.stamps_for_reward,
            "reward_description": config.reward_description.strip(),
            "reward_expires_days": config.reward_expires_days,
            "stamp_rate_limit_minutes": config.stamp_rate_limit_minutes,
        },
    )
    log.info(
        "reward_config_updated",
        tenant_id=tenant_id,
        stamps_for_reward=config.stamps_for_reward,
    )
    return updated
