from datetime import datetime
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def count_in_range(
    tenant_id: str,
    *,
    start: datetime,
    end: datetime,
    action_taken: str | None = None,
) -> int:
    """Count taps for a tenant in [start, end). `action_taken` lets the
    monthly report tally specific outcomes (e.g. 'review_clicked') with the
    same query path."""
    client = get_supabase_admin()
    q = (
        client.table("taps")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
    )
    if action_taken is not None:
        q = q.eq("action_taken", action_taken)
    res = q.limit(1).execute()
    return res.count or 0


def list_in_range(
    tenant_id: str,
    *,
    start: datetime,
    end: datetime,
    limit: int = 10_000,
) -> list[Row]:
    """Fetch tap rows for grouping in Python (top hour, top day, top tag).

    A monthly cron run is the only caller; even a very busy tenant ships well
    under 10k taps/month (target NSM: >50 customers each tapping 5x/month →
    ~250 rows). The cap exists as a runaway-prevention rail.
    """
    client = get_supabase_admin()
    res = (
        client.table("taps")
        .select("tag_id,created_at,action_taken")
        .eq("tenant_id", tenant_id)
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])


def list_customer_review_signals(
    tenant_id: str,
    *,
    since: datetime,
    limit: int = 10_000,
) -> list[Row]:
    """Per-customer tap signals used by the review-nudge cron (S5 Feature 2).

    Returns rows {customer_id, action_taken, created_at} for this tenant since
    `since` (= now - LOOKBACK_DAYS), restricted to identified customers
    (customer_id NOT NULL) and the two actions the nudge cares about. The
    service groups these in Python to decide who earned a stamp but never
    clicked review afterwards — the same "fetch a small window, group in
    Python" shape the monthly report uses, kept because per-tenant tap
    volumes are tiny (~250/month). The 10k cap is a runaway rail, not an
    expected ceiling.

    Anonymous taps (customer_id NULL) are excluded: with no customer we have
    nobody to email and no email/consent to check.
    """
    client = get_supabase_admin()
    res = (
        client.table("taps")
        .select("customer_id,action_taken,created_at")
        .eq("tenant_id", tenant_id)
        .gte("created_at", since.isoformat())
        .not_.is_("customer_id", "null")
        .in_("action_taken", ["stamp_earned", "review_clicked"])
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])


def create(
    *,
    tag_id: str,
    tenant_id: str,
    customer_id: str | None,
    device_type: str,
    interaction_type: str,
    user_agent: str | None,
    ip_hash: str | None,
    action_taken: str | None = None,
) -> Row:
    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "tag_id": tag_id,
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "device_type": device_type,
        "interaction_type": interaction_type,
        "user_agent": user_agent,
        "ip_hash": ip_hash,
        "action_taken": action_taken,
    }
    res = client.table("taps").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("tap not created")
    return rows[0]


def update_action(tap_id: str, action_taken: str) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("taps")
        .update({"action_taken": action_taken})
        .eq("id", tap_id)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"tap {tap_id} not updated")
    return rows[0]
