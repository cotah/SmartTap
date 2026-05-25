from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_tenant_id, require_active_tenant
from app.schemas.tenant import (
    RewardConfigIn,
    TenantSelf,
    TenantSelfResponse,
    TenantSettingsUpdateIn,
)
from app.services import tenant_service

router = APIRouter(tags=["tenants"])


def _to_self(row: dict[str, Any]) -> TenantSelf:
    return TenantSelf(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        business_type=row["business_type"],
        logo_url=row.get("logo_url"),
        primary_color=row["primary_color"],
        accent_color=row["accent_color"],
        google_place_id=row.get("google_place_id"),
        google_review_url=row.get("google_review_url"),
        google_business_url=row.get("google_business_url"),
        stamps_for_reward=int(row.get("stamps_for_reward") or 0),
        reward_description=row.get("reward_description"),
        reward_expires_days=int(row.get("reward_expires_days") or 0),
        stamp_rate_limit_minutes=int(row.get("stamp_rate_limit_minutes") or 0),
        plan=row["plan"],
        is_active=row["is_active"],
        is_founding_member=row.get("is_founding_member", False),
        trial_ends_at=row.get("trial_ends_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/tenant", response_model=TenantSelfResponse)
def get_self_tenant(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> TenantSelfResponse:
    tenant = tenant_service.get_self(tenant_id)
    return TenantSelfResponse(tenant=_to_self(tenant))


@router.post("/tenant/reward-config", response_model=TenantSelfResponse)
def update_reward_config_endpoint(
    body: RewardConfigIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> TenantSelfResponse:
    updated = tenant_service.update_reward_config(
        tenant_id,
        tenant_service.RewardConfig(
            stamps_for_reward=body.stamps_for_reward,
            reward_description=body.reward_description,
            reward_expires_days=body.reward_expires_days,
            stamp_rate_limit_minutes=body.stamp_rate_limit_minutes,
        ),
    )
    return TenantSelfResponse(tenant=_to_self(updated))


@router.put("/tenant/settings", response_model=TenantSelfResponse)
def update_settings_endpoint(
    body: TenantSettingsUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> TenantSelfResponse:
    updated = tenant_service.update_settings(
        tenant_id,
        tenant_service.TenantSettings(
            name=body.name,
            logo_url=body.logo_url,
            primary_color=body.primary_color,
            accent_color=body.accent_color,
            google_place_id=body.google_place_id,
            google_review_url=body.google_review_url,
            google_business_url=body.google_business_url,
        ),
    )
    return TenantSelfResponse(tenant=_to_self(updated))


@router.get("/public/tenants/{slug}")
def get_public_tenant(slug: str) -> dict[str, str]:
    _ = slug
    raise HTTPException(status_code=501, detail="Not implemented yet")
