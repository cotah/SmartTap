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


@dataclass(frozen=True)
class TenantSettings:
    """Partial update bundle.

    For each field: `None` means 'leave as-is'. For nullable fields, passing an
    empty string clears the value in the DB (SET NULL).
    """

    name: str | None
    logo_url: str | None
    primary_color: str | None
    accent_color: str | None
    google_place_id: str | None
    google_review_url: str | None
    google_business_url: str | None


def update_settings(tenant_id: str, settings: TenantSettings) -> Row:
    tenant = tenants.get_by_id(tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found", detail={"tenant_id": tenant_id})

    fields: dict[str, Any] = {}

    if settings.name is not None:
        fields["name"] = settings.name.strip()
    if settings.primary_color is not None:
        fields["primary_color"] = settings.primary_color
    if settings.accent_color is not None:
        fields["accent_color"] = settings.accent_color

    # Nullable fields: explicit None means 'unchanged', empty string means 'clear'.
    for field_name in (
        "logo_url",
        "google_place_id",
        "google_review_url",
        "google_business_url",
    ):
        value = getattr(settings, field_name)
        if value is None:
            continue
        fields[field_name] = value or None  # empty string -> NULL

    if not fields:
        return tenant  # nothing to update

    updated = tenants.update(tenant_id, fields)
    log.info("tenant_settings_updated", tenant_id=tenant_id, fields=list(fields.keys()))
    return updated
