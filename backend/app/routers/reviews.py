"""Google review-response endpoints (S5 Feature 3, Phase A).

The dashboard lists pending reviews with their AI draft and lets the owner
edit, publish (to Google), or dismiss. Reads use get_current_tenant_id (an
expired-trial owner can still see them); mutations use require_active_tenant.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.db import reviews as reviews_db
from app.dependencies import get_current_tenant_id, require_active_tenant
from app.errors import NotFoundError
from app.schemas.review import ReplyUpdateIn, ReviewListResponse, ReviewOut
from app.services import review_response_service

router = APIRouter(tags=["reviews"])


def _to_out(row: dict[str, Any]) -> ReviewOut:
    return ReviewOut(
        id=row["id"],
        google_review_id=row["google_review_id"],
        author=row.get("author"),
        rating=row.get("rating"),
        comment=row.get("comment"),
        created_at_google=row.get("created_at_google"),
        ai_draft=row.get("ai_draft"),
        reply_text=row.get("reply_text"),
        status=row["status"],
        published_at=row.get("published_at"),
        created_at=row["created_at"],
    )


@router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    status: str | None = Query(default="pending"),
    limit: int = Query(default=100, ge=1, le=200),
) -> ReviewListResponse:
    rows = reviews_db.list_for_tenant(tenant_id, status=status, limit=limit)
    return ReviewListResponse(items=[_to_out(r) for r in rows])


@router.put("/reviews/{review_id}/reply", response_model=ReviewOut)
def update_reply(
    review_id: str,
    body: ReplyUpdateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> ReviewOut:
    """Save the owner's edited reply text (does not publish)."""
    existing = reviews_db.get_owned(tenant_id, review_id)
    if existing is None:
        raise NotFoundError("Review not found")
    row = reviews_db.update(review_id, {"reply_text": body.reply_text})
    return _to_out(row)


@router.post("/reviews/{review_id}/publish", response_model=ReviewOut)
def publish_review(
    review_id: str,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> ReviewOut:
    """Publish the approved reply to Google. Uses reply_text, falling back to
    the AI draft. Raises (404/400) handled by the global error handlers."""
    row = review_response_service.publish_review(tenant_id=tenant_id, review_id=review_id)
    return _to_out(row)


@router.post("/reviews/{review_id}/dismiss", response_model=ReviewOut)
def dismiss_review(
    review_id: str,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> ReviewOut:
    existing = reviews_db.get_owned(tenant_id, review_id)
    if existing is None:
        raise NotFoundError("Review not found")
    row = reviews_db.update(review_id, {"status": "dismissed"})
    return _to_out(row)
