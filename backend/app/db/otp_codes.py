"""DB access for customer phone OTP codes (Sprint 5.6).

Mirrors the owner-bot OTP table (db/whatsapp.py) but scoped by
(tenant_id, phone): the same number can be a different customer in each
tenant. Codes are stored hashed; the service owns the verification logic.
"""

from datetime import datetime
from typing import Any, cast

from postgrest import CountMethod

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]

_TABLE = "customer_otp_codes"


def create(
    *,
    tenant_id: str,
    phone: str,
    code_hash: str,
    expires_at: datetime,
) -> Row:
    client = get_supabase_admin()
    res = (
        client.table(_TABLE)
        .insert(
            {
                "tenant_id": tenant_id,
                "phone": phone,
                "code_hash": code_hash,
                "expires_at": expires_at.isoformat(),
            }
        )
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("customer_otp not created")
    return rows[0]


def get_latest(tenant_id: str, phone: str) -> Row | None:
    """Most recently created code for this phone+tenant (consumed or not). The
    service checks consumed_at / expires_at / attempts itself."""
    client = get_supabase_admin()
    res = (
        client.table(_TABLE)
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def increment_attempts(otp_id: str) -> int:
    """Bump attempts by 1 and return the new value. Read-then-write is fine —
    one customer, one code, not a high-concurrency path."""
    client = get_supabase_admin()
    cur = (
        client.table(_TABLE)
        .select("attempts")
        .eq("id", otp_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], cur.data or [])
    current = int(rows[0].get("attempts") or 0) if rows else 0
    new_value = current + 1
    client.table(_TABLE).update({"attempts": new_value}).eq("id", otp_id).execute()
    return new_value


def consume(otp_id: str, consumed_at: datetime) -> None:
    client = get_supabase_admin()
    client.table(_TABLE).update({"consumed_at": consumed_at.isoformat()}).eq(
        "id", otp_id
    ).execute()


def count_since(tenant_id: str, phone: str, since: datetime) -> int:
    """How many codes were created for this phone+tenant since `since` — drives
    the per-minute cooldown and per-hour send cap."""
    client = get_supabase_admin()
    res = (
        client.table(_TABLE)
        .select("id", count=CountMethod.exact)
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .gte("created_at", since.isoformat())
        .limit(1)
        .execute()
    )
    return res.count or 0
