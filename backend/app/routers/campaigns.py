from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_tenant_id, require_active_tenant
from app.schemas.campaign import (
    CampaignCreateIn,
    CampaignListResponse,
    CampaignOut,
    CampaignStatusUpdateIn,
    CampaignUpdateIn,
)
from app.services import campaign_service

router = APIRouter(tags=["campaigns"])


def _to_out(row: dict[str, Any]) -> CampaignOut:
    """Flatten the JSONB config into a flat field so the API doesn't leak
    storage details. The DB nests `multiplier` under `config` for future
    flexibility (recurrence patterns, etc.) but the wire shape is flat."""
    config = row.get("config") or {}
    try:
        multiplier = int(config.get("multiplier", 1)) if isinstance(config, dict) else 1
    except (TypeError, ValueError):
        multiplier = 1
    return CampaignOut(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        type=row["type"],
        status=row["status"],
        multiplier=multiplier,
        starts_at=row.get("starts_at"),
        ends_at=row.get("ends_at"),
        created_at=row["created_at"],
    )


@router.get("/campaigns", response_model=CampaignListResponse)
def list_campaigns(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> CampaignListResponse:
    """Read-only — uses get_current_tenant_id, not require_active_tenant, so
    expired-trial owners can still see what they had set up."""
    rows = campaign_service.list_for_tenant(tenant_id)
    return CampaignListResponse(items=[_to_out(r) for r in rows])


@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    body: CampaignCreateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> CampaignOut:
    row = campaign_service.create_double_stamp(
        tenant_id=tenant_id,
        name=body.name,
        multiplier=body.multiplier,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        status=body.status,
    )
    return _to_out(row)


@router.patch("/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: str,
    body: CampaignUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> CampaignOut:
    row = campaign_service.update_campaign(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        name=body.name,
        multiplier=body.multiplier,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    return _to_out(row)


@router.post("/campaigns/{campaign_id}/status", response_model=CampaignOut)
def change_campaign_status(
    campaign_id: str,
    body: CampaignStatusUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> CampaignOut:
    row = campaign_service.change_status(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        new_status=body.status,
    )
    return _to_out(row)
