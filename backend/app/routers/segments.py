"""Customer segment endpoints (S4-W4)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import get_current_tenant_id, require_active_tenant
from app.schemas.segment import (
    SegmentCreateIn,
    SegmentCriteria,
    SegmentCustomerPreview,
    SegmentListResponse,
    SegmentOut,
    SegmentPreviewResponse,
    SegmentUpdateIn,
)
from app.services import segment_service

router = APIRouter(tags=["segments"])


def _to_out(row: dict[str, Any]) -> SegmentOut:
    """Re-validate the stored JSONB criteria so the API only ever serialises
    well-formed payloads, even if a row was written by an older code
    version with a slightly different shape."""
    raw_criteria = row.get("criteria") or {}
    known = SegmentCriteria.model_fields.keys()
    cleaned = (
        {k: v for k, v in raw_criteria.items() if k in known}
        if isinstance(raw_criteria, dict)
        else {}
    )
    criteria = SegmentCriteria.model_validate(cleaned)
    return SegmentOut(
        id=row["id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        criteria=criteria,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _preview_row(row: dict[str, Any]) -> SegmentCustomerPreview:
    return SegmentCustomerPreview(
        id=row["id"],
        name=row.get("name"),
        phone=row.get("phone"),
        email=row.get("email"),
        current_stamps=int(row.get("current_stamps") or 0),
        total_visits=int(row.get("total_visits") or 0),
        last_visit_at=row.get("last_visit_at"),
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("/segments", response_model=SegmentListResponse)
def list_segments(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> SegmentListResponse:
    """Read-only — uses get_current_tenant_id so expired-trial owners can
    still see their saved segments (mirrors the campaigns list contract)."""
    rows = segment_service.list_for_tenant(tenant_id)
    return SegmentListResponse(items=[_to_out(r) for r in rows])


@router.post("/segments", response_model=SegmentOut)
def create_segment(
    body: SegmentCreateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> SegmentOut:
    row = segment_service.create_segment(
        tenant_id=tenant_id, name=body.name, criteria=body.criteria
    )
    return _to_out(row)


@router.patch("/segments/{segment_id}", response_model=SegmentOut)
def update_segment(
    segment_id: str,
    body: SegmentUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> SegmentOut:
    row = segment_service.update_segment(
        tenant_id=tenant_id,
        segment_id=segment_id,
        name=body.name,
        criteria=body.criteria,
    )
    return _to_out(row)


@router.delete("/segments/{segment_id}", status_code=204)
def delete_segment(
    segment_id: str,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> Response:
    """Hard delete — see segment_service.delete_segment for the scope note."""
    segment_service.delete_segment(tenant_id=tenant_id, segment_id=segment_id)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


@router.get(
    "/segments/{segment_id}/preview",
    response_model=SegmentPreviewResponse,
)
def preview_segment(
    segment_id: str,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    limit: int = Query(default=20, ge=1, le=200),
) -> SegmentPreviewResponse:
    """Run the segment's criteria right now and return total + first `limit`
    matches. Read-only, so available even on expired-trial tenants.

    The frontend triggers this on a "Preview" button click — never on every
    keystroke — to keep backend load predictable.
    """
    total, rows, evaluated_at = segment_service.evaluate(
        tenant_id=tenant_id, segment_id=segment_id, limit=limit
    )
    return SegmentPreviewResponse(
        total=total,
        items=[_preview_row(r) for r in rows],
        evaluated_at=evaluated_at,
    )


@router.post(
    "/segments/preview",
    response_model=SegmentPreviewResponse,
)
def preview_unsaved_segment(
    body: SegmentCreateIn,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    limit: int = Query(default=20, ge=1, le=200),
) -> SegmentPreviewResponse:
    """Preview a criteria payload that hasn't been saved yet. Used by the
    create-segment form so the merchant can experiment before clicking Save.

    `name` in the body is required by the schema but not used for the
    evaluation — accepting the full SegmentCreateIn keeps the wire shape
    identical to /segments POST so the frontend can send the same payload."""
    total, rows, evaluated_at = segment_service.evaluate_unsaved(
        tenant_id=tenant_id, criteria=body.criteria, limit=limit
    )
    return SegmentPreviewResponse(
        total=total,
        items=[_preview_row(r) for r in rows],
        evaluated_at=evaluated_at,
    )
