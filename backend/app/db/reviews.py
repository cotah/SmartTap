"""DB access for Google reviews + their AI drafts (S5 Feature 3).

Pure CRUD. Dedupe is enforced by the UNIQUE (tenant_id, google_review_id)
constraint; `exists` lets the cron skip reviews it already stored without
relying on catching the constraint error.
"""

from datetime import datetime
from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]

Status = str  # pending | published | dismissed | failed


def exists(tenant_id: str, google_review_id: str) -> bool:
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("google_review_id", google_review_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def create(
    *,
    tenant_id: str,
    google_review_id: str,
    author: str | None,
    rating: int | None,
    comment: str | None,
    created_at_google: str | None,
    ai_draft: str | None,
    status: Status = "pending",
) -> Row:
    client = get_supabase_admin()
    payload: Row = {
        "tenant_id": tenant_id,
        "google_review_id": google_review_id,
        "author": author,
        "rating": rating,
        "comment": comment,
        "created_at_google": created_at_google,
        "ai_draft": ai_draft,
        "status": status,
    }
    res = client.table("reviews").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("review not created")
    return rows[0]


def get_owned(tenant_id: str, review_id: str) -> Row | None:
    """Fetch a review scoped to the tenant — returns None if it doesn't exist
    or belongs to another tenant (caller maps to 404, no cross-tenant leak)."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("*")
        .eq("id", review_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def list_for_tenant(tenant_id: str, *, status: str | None = None, limit: int = 100) -> list[Row]:
    client = get_supabase_admin()
    query = (
        client.table("reviews")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at_google", desc=True)
    )
    if status is not None:
        query = query.eq("status", status)
    res = query.limit(limit).execute()
    return cast(list[Row], res.data or [])


def list_all_ratings(tenant_id: str, *, limit: int = 5000) -> list[int | None]:
    """Fetch just the `rating` of every review for a tenant, for the summary
    header. Reviews are low-volume (a busy small business has dozens, not
    thousands); the cap is a runaway rail, mirroring db.taps.list_in_range."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("rating")
        .eq("tenant_id", tenant_id)
        .limit(limit)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return [r.get("rating") for r in rows]


def update(review_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("reviews").update(fields).eq("id", review_id).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"review {review_id} not updated")
    return rows[0]


def mark_published(review_id: str, reply_text: str, published_at: datetime) -> Row:
    return update(
        review_id,
        {
            "reply_text": reply_text,
            "status": "published",
            "published_at": published_at.isoformat(),
        },
    )
