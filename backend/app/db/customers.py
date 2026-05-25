import secrets
from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


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
