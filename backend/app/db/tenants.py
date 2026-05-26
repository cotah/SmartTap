from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


def get_by_id(tenant_id: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("tenants").select("*").eq("id", tenant_id).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_slug(slug: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("tenants").select("*").eq("slug", slug).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_stripe_subscription(subscription_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("tenants")
        .select("*")
        .eq("stripe_subscription_id", subscription_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_stripe_customer(customer_id: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("tenants")
        .select("*")
        .eq("stripe_customer_id", customer_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def update(tenant_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("tenants").update(fields).eq("id", tenant_id).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"tenant {tenant_id} not updated")
    return rows[0]


def create(fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("tenants").insert(fields).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("tenant not created")
    return rows[0]


def list_active_for_cron(*, limit: int = 1000) -> list[Row]:
    """Tenants the daily cron should consider for outbound work.

    "Active" here means `is_active=true` — paying customers AND tenants still
    inside their trial. We deliberately include trial tenants so they get to
    see the reactivation flow during the evaluation period.

    The list is small for the foreseeable future (target: 200 tenants by month
    24), so a single page is fine. The `limit` exists as a safety rail in
    case we forget to paginate later — at 1000 rows we'd still rather hit
    the cap than DoS the cron with a runaway scan.

    Only the columns the cron actually needs are selected, which keeps the
    response light when we later add heavy columns (config blobs, etc.).
    """
    client = get_supabase_admin()
    res = (
        client.table("tenants")
        .select("id,name,stamps_for_reward,reward_description")
        .eq("is_active", True)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])
