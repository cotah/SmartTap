"""WhatsApp owner bot orchestration (S5 Feature 1, Phase A).

Owns the auth state machine (WhatsApp-first + email OTP) and, once a number is
verified, dispatches the owner's questions to Claude with the read-only tools.

`handle_inbound(phone, body)` is pure-ish: it does DB / email / Anthropic work
and RETURNS the reply text. The webhook router is responsible for actually
sending that text back via Twilio. This split keeps the service testable
without a Twilio round-trip.

Security policy (see spec §3/§9):
    - Anti-enumeration: the "we emailed you a code" reply is identical whether
      or not the email matches a tenant owner.
    - OTP: 6 digits, sha256-hashed at rest, 10-min TTL, 5 attempts, then a
      1-hour lockout. Max 3 code requests per phone per hour.
    - The tenant_id is resolved here from the verified link and injected into
      the tool dispatch — Claude never selects it.
"""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.db import tenant_members, users, whatsapp
from app.services import anthropic_client, bot_tools, email_service

log = structlog.get_logger(__name__)

OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
LOCKOUT_HOURS = 1
OTP_REQUESTS_PER_HOUR = 3
CODE_LENGTH = 6

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Messages kept short — they're WhatsApp replies.
MSG_ASK_EMAIL = (
    "Hi! To link your SmartTap account, reply with the email address you use to "
    "sign in."
)
MSG_NOT_AN_EMAIL = "That doesn't look like an email. Please reply with your account email."
MSG_CODE_SENT = (
    "If that account exists, I've emailed a 6-digit code. Reply here with the code "
    "to finish linking."
)
MSG_LINKED = (
    "Your account is linked. Ask me anything about your business — for example "
    "\"How many customers this week?\" or \"Who hasn't come back?\""
)
MSG_CODE_EXPIRED = "That code has expired. Reply with your account email to get a new one."
MSG_LOCKED = "Too many attempts. Please try again in about an hour."
MSG_RATE_LIMITED = "You've requested several codes. Please wait a bit before trying again."
MSG_BOT_UNAVAILABLE = "The assistant isn't available right now. Please try again later."


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _normalise_phone(phone: str) -> str:
    """Store/look up bare E.164. Inbound `From` is `whatsapp:+353...`."""
    return phone.strip().removeprefix("whatsapp:").strip()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _is_locked(link: dict[str, Any], now: datetime) -> bool:
    until = link.get("lockout_until")
    if not isinstance(until, str) or not until:
        return False
    try:
        ts = datetime.fromisoformat(until.replace("Z", "+00:00"))
    except ValueError:
        return False
    return ts > now


def handle_inbound(phone: str, body: str, *, now: datetime | None = None) -> str:
    """Process one inbound WhatsApp message and return the reply text."""
    current = _now(now)
    phone = _normalise_phone(phone)
    text = (body or "").strip()

    link = whatsapp.get_link_by_phone(phone)
    if link is None:
        whatsapp.create_link(phone, state="awaiting_email")
        return MSG_ASK_EMAIL

    if _is_locked(link, current):
        return MSG_LOCKED

    state = link.get("state")
    if state == "verified":
        return _handle_verified(link, text)
    if state == "awaiting_code":
        return _handle_code(phone, link, text, current)
    # Default / awaiting_email
    return _handle_email(phone, text, current)


def _handle_email(phone: str, text: str, now: datetime) -> str:
    if not _EMAIL_RE.match(text):
        return MSG_NOT_AN_EMAIL

    # Rate-limit OTP requests per phone.
    window_start = now - timedelta(hours=1)
    if whatsapp.count_otps_since(phone, window_start) >= OTP_REQUESTS_PER_HOUR:
        return MSG_RATE_LIMITED

    tenant_id = _resolve_tenant_for_email(text)
    if tenant_id is not None:
        code = f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"
        whatsapp.create_otp(
            phone=phone,
            email=text,
            tenant_id=tenant_id,
            code_hash=_hash_code(code),
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        )
        whatsapp.update_link(phone, {"state": "awaiting_code", "pending_email": text})
        # Email send is best-effort; failure logs inside email_service.
        email_service.send_whatsapp_otp(to=text, code=code)
        log.info("whatsapp_otp_sent", phone_suffix=phone[-4:])

    # Anti-enumeration: identical reply whether or not the email matched.
    return MSG_CODE_SENT


def _resolve_tenant_for_email(email: str) -> str | None:
    """email -> tenant_id (owner's tenant), or None. Picks the owner membership
    if present, else the earliest membership."""
    user_id = users.get_user_id_by_email(email)
    if not user_id:
        return None
    memberships = tenant_members.list_for_user(user_id)
    if not memberships:
        return None
    owner = next((m for m in memberships if m.get("role") == "owner"), memberships[0])
    tid = owner.get("tenant_id")
    return str(tid) if tid else None


def _handle_code(phone: str, link: dict[str, Any], text: str, now: datetime) -> str:
    code = text.strip()
    otp = whatsapp.get_latest_otp(phone)
    if otp is None or otp.get("consumed_at"):
        return MSG_CODE_EXPIRED

    expires = otp.get("expires_at")
    if isinstance(expires, str):
        try:
            if datetime.fromisoformat(expires.replace("Z", "+00:00")) <= now:
                return MSG_CODE_EXPIRED
        except ValueError:
            return MSG_CODE_EXPIRED

    if int(otp.get("attempts") or 0) >= MAX_OTP_ATTEMPTS:
        whatsapp.update_link(
            phone, {"lockout_until": (now + timedelta(hours=LOCKOUT_HOURS)).isoformat()}
        )
        return MSG_LOCKED

    if hmac.compare_digest(str(otp.get("code_hash") or ""), _hash_code(code)):
        whatsapp.consume_otp(str(otp["id"]), now)
        whatsapp.update_link(
            phone,
            {
                "state": "verified",
                "tenant_id": otp.get("tenant_id"),
                "verified_at": now.isoformat(),
                "pending_email": None,
            },
        )
        log.info("whatsapp_link_verified", phone_suffix=phone[-4:])
        return MSG_LINKED

    attempts = whatsapp.increment_otp_attempts(str(otp["id"]))
    if attempts >= MAX_OTP_ATTEMPTS:
        whatsapp.update_link(
            phone, {"lockout_until": (now + timedelta(hours=LOCKOUT_HOURS)).isoformat()}
        )
        return MSG_LOCKED
    remaining = MAX_OTP_ATTEMPTS - attempts
    return f"That code isn't right. {remaining} attempt(s) left."


def _handle_verified(link: dict[str, Any], text: str) -> str:
    tenant_id = link.get("tenant_id")
    if not isinstance(tenant_id, str):
        # Shouldn't happen for a verified link, but never leak another tenant.
        return MSG_BOT_UNAVAILABLE

    if not anthropic_client.is_configured():
        return MSG_BOT_UNAVAILABLE

    from app.db import tenants

    tenant = tenants.get_by_id(tenant_id) or {}
    system = _system_prompt(tenant)

    def dispatch(name: str, tool_input: dict[str, Any]) -> str:
        return bot_tools.execute(name, tenant_id, tool_input)

    return anthropic_client.run_conversation(
        system=system,
        user_text=text,
        tools=bot_tools.TOOLS,
        dispatch=dispatch,
    )


def _system_prompt(tenant: dict[str, Any]) -> str:
    name = (tenant.get("name") or "the business").strip()
    btype = (tenant.get("business_type") or "local business").strip()
    return (
        f"You are the SmartTap assistant for {name}, a {btype} in Ireland. You are "
        "talking to the owner over WhatsApp. Answer using ONLY the data returned by "
        "the tools — never invent numbers. Keep replies short and friendly, suitable "
        "for a phone screen. Reply in the same language the owner writes in "
        "(Portuguese or English). If the tools don't have what they asked for, say so "
        "plainly. You can only read data right now; you cannot send messages, create "
        "campaigns, or change anything yet."
    )
