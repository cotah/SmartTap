import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]

FilterMode = Literal["all", "active", "at_risk", "has_reward"]
SortMode = Literal["recent", "visits", "stamps"]

AT_RISK_DAYS = 30


def get_by_id(customer_id: str) -> Row | None:
    client = get_supabase_admin()
    res = client.table("customers").select("*").eq("id", customer_id).limit(1).execute()
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_phone(tenant_id: str, phone: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("customers")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def get_by_magic_token(magic_link_token: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("customers")
        .select("*")
        .eq("magic_link_token", magic_link_token)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def count_created_in_range(
    tenant_id: str, *, start: datetime, end: datetime
) -> int:
    """New signups for a tenant in [start, end). Used by the monthly report
    to derive 'new customers this month'."""
    client = get_supabase_admin()
    res = (
        client.table("customers")
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
        .limit(1)
        .execute()
    )
    return res.count or 0


def find_inactive_for_reactivation(
    *,
    tenant_id: str,
    inactive_cutoff: datetime,
    cooldown_cutoff: datetime,
    limit: int = 500,
) -> list[Row]:
    """Customers eligible to receive a reactivation email right now.

    The cron passes:
        inactive_cutoff = now - 30 days   (last_visit_at must be older than this)
        cooldown_cutoff = now - 90 days   (don't re-email until at least this old)

    Filters enforced in SQL — we never pull a customer who didn't consent or
    doesn't have an email, so accidentally calling `send_reactivation` on the
    full result is safe by construction.

    `limit` caps the per-tenant batch so a tenant with thousands of dormant
    customers doesn't monopolize the cron run; the next day picks up the rest.
    """
    client = get_supabase_admin()
    iso_inactive = inactive_cutoff.isoformat()
    iso_cooldown = cooldown_cutoff.isoformat()

    # gdpr_consent + email-not-null are duplicated as filters here (already in
    # the partial index) so even if the index gets dropped, we still respect
    # consent.
    res = (
        client.table("customers")
        .select("id,name,email,current_stamps,magic_link_token,last_visit_at")
        .eq("tenant_id", tenant_id)
        .eq("gdpr_consent", True)
        .not_.is_("email", "null")
        .not_.is_("last_visit_at", "null")
        .lt("last_visit_at", iso_inactive)
        # PostgREST has no native "x IS NULL OR x < y" — `or_` is the escape
        # hatch. The string syntax is finicky; keep it literal and tested.
        .or_(
            f"last_reactivation_sent_at.is.null,"
            f"last_reactivation_sent_at.lt.{iso_cooldown}"
        )
        .order("last_visit_at", desc=False)  # oldest no-show first
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])


def mark_reactivation_sent(customer_id: str, sent_at: datetime) -> None:
    """Best-effort marker for cooldown enforcement. Writes BEFORE the actual
    email send is acknowledged so that a partial failure (cron crash mid-loop)
    won't re-send to the same customer on the next run — at worst a customer
    misses one email cycle, which is far better than getting it twice."""
    client = get_supabase_admin()
    client.table("customers").update(
        {"last_reactivation_sent_at": sent_at.isoformat()}
    ).eq("id", customer_id).execute()


def revoke_consent_via_magic_token(magic_link_token: str) -> Row | None:
    """One-click GDPR opt-out from an email link. Idempotent: hitting the URL
    twice after a successful opt-out still returns the row and stays at
    consent=false. Returns None if the token doesn't match any customer
    (treated by the caller as a soft 404 — never reveal which is which)."""
    client = get_supabase_admin()
    res = (
        client.table("customers")
        .update(
            {
                "gdpr_consent": False,
                "gdpr_consent_at": None,
            }
        )
        .eq("magic_link_token", magic_link_token)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create(
    *,
    tenant_id: str,
    phone: str | None,
    name: str | None,
    birthday: str | None,
    gdpr_consent: bool,
    gdpr_consent_text: str | None,
) -> Row:
    from datetime import UTC, datetime

    client = get_supabase_admin()
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "phone": phone,
        "name": name,
        "birthday": birthday,
        "gdpr_consent": gdpr_consent,
        "gdpr_consent_text": gdpr_consent_text,
        "magic_link_token": secrets.token_urlsafe(24),
    }
    if gdpr_consent:
        payload["gdpr_consent_at"] = datetime.now(UTC).isoformat()
    res = client.table("customers").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("customer not created")
    return rows[0]


def update(customer_id: str, fields: dict[str, Any]) -> Row:
    client = get_supabase_admin()
    res = client.table("customers").update(fields).eq("id", customer_id).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError(f"customer {customer_id} not updated")
    return rows[0]


def find_by_criteria(
    *,
    tenant_id: str,
    visits_min: int | None = None,
    visits_max: int | None = None,
    stamps_min: int | None = None,
    stamps_max: int | None = None,
    last_visit_after: datetime | None = None,
    last_visit_before: datetime | None = None,
    created_after: datetime | None = None,
    has_email: bool | None = None,
    has_phone: bool | None = None,
    gdpr_consent_only: bool | None = None,
    limit: int = 20,
) -> tuple[list[Row], int]:
    """Evaluate a segment criteria block against customers for this tenant.

    Returns (rows_for_preview, total_count). The count is the unpaginated
    match count after all filters — so the dashboard can say "123 customers
    match (showing first 20)" without a second roundtrip.

    The function takes *resolved* datetime cutoffs rather than day counts so
    the service layer owns the "now" reference and tests can pin it. Each
    None argument is a no-op filter. AND semantics throughout.
    """
    client = get_supabase_admin()
    query = (
        client.table("customers")
        .select(
            "id,name,phone,email,current_stamps,total_visits,last_visit_at,created_at",
            count=CountMethod.exact,
        )
        .eq("tenant_id", tenant_id)
    )

    if visits_min is not None:
        query = query.gte("total_visits", visits_min)
    if visits_max is not None:
        query = query.lte("total_visits", visits_max)
    if stamps_min is not None:
        query = query.gte("current_stamps", stamps_min)
    if stamps_max is not None:
        query = query.lte("current_stamps", stamps_max)
    if last_visit_after is not None:
        # "Visited within last N days" — recent activity. NULL last_visit_at
        # rows are correctly excluded by the >= operator.
        query = query.gte("last_visit_at", last_visit_after.isoformat())
    if last_visit_before is not None:
        # "No visit in N+ days" — dormant. Same NULL-exclusion semantics.
        query = query.lt("last_visit_at", last_visit_before.isoformat())
    if created_after is not None:
        query = query.gte("created_at", created_after.isoformat())
    if has_email is True:
        query = query.not_.is_("email", "null")
    elif has_email is False:
        query = query.is_("email", "null")
    if has_phone is True:
        query = query.not_.is_("phone", "null")
    elif has_phone is False:
        query = query.is_("phone", "null")
    if gdpr_consent_only is True:
        query = query.eq("gdpr_consent", True)

    query = query.order("last_visit_at", desc=True)
    res = query.range(0, max(0, limit - 1)).execute()
    rows = cast(list[Row], res.data or [])
    total = res.count or 0
    return rows, total


def list_for_tenant(
    *,
    tenant_id: str,
    search: str | None,
    filter_mode: FilterMode,
    sort: SortMode,
    page: int,
    limit: int,
    stamps_for_reward: int,
) -> tuple[list[Row], int]:
    """List customers for a tenant with search, filter, sort, pagination.

    Returns (rows, total_count). The total is the unpaginated count after filters.
    """
    client = get_supabase_admin()
    query = (
        client.table("customers")
        .select(
            "id,name,phone,current_stamps,total_visits,last_visit_at,created_at",
            count=CountMethod.exact,
        )
        .eq("tenant_id", tenant_id)
    )

    if search:
        # ilike against name OR phone (postgrest 'or' syntax)
        safe = search.replace(",", " ").replace("(", "").replace(")", "")
        pattern = f"*{safe}*"
        query = query.or_(f"name.ilike.{pattern},phone.ilike.{pattern}")

    now = datetime.now(UTC)
    at_risk_cutoff = (now - timedelta(days=AT_RISK_DAYS)).isoformat()

    if filter_mode == "active":
        query = query.gte("last_visit_at", at_risk_cutoff)
    elif filter_mode == "at_risk":
        query = query.lt("last_visit_at", at_risk_cutoff)
    elif filter_mode == "has_reward":
        if stamps_for_reward > 0:
            query = query.gte("current_stamps", stamps_for_reward)
        else:
            # No reward threshold configured → nobody qualifies.
            return [], 0

    if sort == "visits":
        query = query.order("total_visits", desc=True)
    elif sort == "stamps":
        query = query.order("current_stamps", desc=True)
    else:  # recent
        query = query.order("created_at", desc=True)

    start = (page - 1) * limit
    end = start + limit - 1
    res = query.range(start, end).execute()
    rows = cast(list[Row], res.data or [])
    total = res.count or 0
    return rows, total
