"""DB access for Google reviews + their AI drafts (S5 Feature 3).

Pure CRUD. Dedupe is enforced by the UNIQUE (tenant_id, google_review_id)
constraint (partial index after migration 018); `exists` lets the cron skip
reviews it already stored without relying on catching the constraint error.
"""

from datetime import datetime
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]

Status = str  # pending | published | dismissed | failed | approved


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
    google_review_id: str | None,
    author: str | None,
    rating: int | None,
    comment: str | None,
    created_at_google: str | None,
    ai_draft: str | None,
    status: Status = "pending",
    source: str = "google",
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
        "source": source,
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


def count_received_in_range(tenant_id: str, *, start: datetime, end: datetime) -> int:
    """Reviews the business RECEIVED in [start, end), keyed on the Google-side
    creation time (`created_at_google`), not our ingestion time — a cron that
    catches up on a backlog shouldn't inflate the current month."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .gte("created_at_google", start.isoformat())
        .lt("created_at_google", end.isoformat())
        .execute()
    )
    return int(res.count or 0)


def count_published_in_range(tenant_id: str, *, start: datetime, end: datetime) -> int:
    """Replies PUBLISHED in [start, end) — a review received in April but
    answered in May counts toward May's 'responded' number."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .eq("status", "published")
        .gte("published_at", start.isoformat())
        .lt("published_at", end.isoformat())
        .execute()
    )
    return int(res.count or 0)


def list_ratings_in_range(
    tenant_id: str, *, start: datetime, end: datetime, limit: int = 5000
) -> list[int | None]:
    """Ratings of reviews received in [start, end) for the monthly average.
    Same runaway-rail cap rationale as `list_all_ratings`."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("rating")
        .eq("tenant_id", tenant_id)
        .gte("created_at_google", start.isoformat())
        .lt("created_at_google", end.isoformat())
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


def list_reply_examples(tenant_id: str, *, limit: int = 50) -> list[Row]:
    """Approved/published replies used as few-shot examples for new drafts.
    Newest-first; the service re-ranks by rating proximity to the review
    being answered."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("rating, comment, reply_text")
        .eq("tenant_id", tenant_id)
        .in_("status", ["approved", "published"])
        .not_.is_("reply_text", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])
