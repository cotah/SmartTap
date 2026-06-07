"""NFC tag endpoints (S5-W0)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.dependencies import get_current_tenant_id, require_active_tenant
from app.schemas.nfc_tag import (
    NfcTagCreateIn,
    NfcTagListResponse,
    NfcTagOut,
    NfcTagUpdateIn,
)
from app.services import nfc_tag_service

router = APIRouter(tags=["tags"])


def _to_out(row: dict[str, Any]) -> NfcTagOut:
    return NfcTagOut(
        id=row["id"],
        tenant_id=row["tenant_id"],
        tag_uuid=row["tag_uuid"],
        tag_number=row.get("tag_number"),
        format=row["format"],
        color=row["color"],
        location_name=row.get("location_name"),
        is_active=bool(row.get("is_active", True)),
        deployed_at=row.get("deployed_at"),
        created_at=row["created_at"],
    )


@router.get("/tags", response_model=NfcTagListResponse)
def list_tags(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> NfcTagListResponse:
    """Read-only — uses get_current_tenant_id so expired-trial owners can
    still inspect their tags."""
    rows = nfc_tag_service.list_for_tenant(tenant_id)
    return NfcTagListResponse(items=[_to_out(r) for r in rows])


@router.post("/tags", response_model=NfcTagOut)
def create_tag(
    body: NfcTagCreateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> NfcTagOut:
    row = nfc_tag_service.create_tag(
        tenant_id=tenant_id,
        format=body.format,
        color=body.color,
        location_name=body.location_name,
    )
    return _to_out(row)


@router.patch("/tags/{tag_id}", response_model=NfcTagOut)
def update_tag(
    tag_id: str,
    body: NfcTagUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> NfcTagOut:
    # `model_fields_set` distinguishes "not sent" from "sent as null".
    # That matters for location_name: clearing it (set to null/empty) is
    # a different intent from leaving it alone.
    location_explicit = "location_name" in body.model_fields_set
    row = nfc_tag_service.update_tag(
        tenant_id=tenant_id,
        tag_id=tag_id,
        format=body.format,
        color=body.color,
        location_name=body.location_name,
        is_active=body.is_active,
        location_name_explicitly_set=location_explicit,
    )
    return _to_out(row)
