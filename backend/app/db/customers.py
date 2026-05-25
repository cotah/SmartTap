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
