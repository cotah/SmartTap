"""DB access for the WhatsApp owner bot (S5 Feature 1, Phase A).

Two tables: `whatsapp_links` (phone → tenant + auth state machine) and
`whatsapp_otp_codes` (hashed email OTPs). This layer is pure CRUD — the state
machine and all policy live in `whatsapp_bot_service`.
"""

from datetime import datetime
from typing import Any, cast

from app.services.supabase_client import get_supabase_admin

Row = dict[str, Any]


# ---------------------------------------------------------------------------
# whatsapp_links
# ---------------------------------------------------------------------------


def get_link_by_phone(phone: str) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("whatsapp_links")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def create_link(phone: str, *, state: str = "awaiting_email") -> Row:
    client = get_supabase_admin()
    res = (
        client.table("whatsapp_links")
        .insert({"phone": phone, "state": state})
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("whatsapp_link not created")
    return rows[0]


def update_link(phone: str, fields: dict[str, Any]) -> Row | None:
    client = get_supabase_admin()
    res = (
        client.table("whatsapp_links")
        .update(fields)
        .eq("phone", phone)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# whatsapp_otp_codes
# ---------------------------------------------------------------------------


def create_otp(
    *,
    phone: str,
    email: str,
    tenant_id: str,
    code_hash: str,
    expires_at: datetime,
) -> Row:
    client = get_supabase_admin()
    res = (
        client.table("whatsapp_otp_codes")
        .insert(
            {
                "phone": phone,
                "email": email,
                "tenant_id": tenant_id,
                "code_hash": code_hash,
                "expires_at": expires_at.isoformat(),
            }
        )
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("whatsapp_otp not created")
    return rows[0]


def get_latest_otp(phone: str) -> Row | None:
    """Most recently created OTP for this phone (consumed or not). The service
    checks consumed_at / expires_at / attempts itself."""
    client = get_supabase_admin()
    res = (
        client.table("whatsapp_otp_codes")
        .select("*")
        .eq("phone", phone)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], res.data or [])
    return rows[0] if rows else None


def increment_otp_attempts(otp_id: str) -> int:
    """Bump attempts by 1 and return the new value. Read-then-write is fine —
    OTP verification is not a high-concurrency path (one owner, one code)."""
    client = get_supabase_admin()
    cur = (
        client.table("whatsapp_otp_codes")
        .select("attempts")
        .eq("id", otp_id)
        .limit(1)
        .execute()
    )
    rows = cast(list[Row], cur.data or [])
    current = int(rows[0].get("attempts") or 0) if rows else 0
    new_value = current + 1
    client.table("whatsapp_otp_codes").update({"attempts": new_value}).eq(
        "id", otp_id
    ).execute()
    return new_value


def consume_otp(otp_id: str, consumed_at: datetime) -> None:
    client = get_supabase_admin()
    client.table("whatsapp_otp_codes").update(
        {"consumed_at": consumed_at.isoformat()}
    ).eq("id", otp_id).execute()


def count_otps_since(phone: str, since: datetime) -> int:
    """How many OTPs were created for this phone since `since` — drives the
    per-hour send rate limit."""
    from postgrest import CountMethod

    client = get_supabase_admin()
    res = (
        client.table("whatsapp_otp_codes")
        .select("id", count=CountMethod.exact)
        .eq("phone", phone)
        .gte("created_at", since.isoformat())
        .limit(1)
        .execute()
    )
    return res.count or 0
