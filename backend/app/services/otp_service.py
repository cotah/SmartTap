"""Customer phone OTP — permanent identification without cookies (Sprint 5.6).

A returning customer who lost their `smarttap_magic` cookie enters their phone
on /t/[uuid]; if they're already a customer of that tenant we text a 4-digit
code, and on verify we hand back their magic_link_token so the page can set the
same cookie and re-tap (which awards this visit's stamp via the normal flow).

Security posture:
    - Anti-enumeration: request_code always returns silently. We only create a
      code + send an SMS when the phone is actually a customer; the endpoint
      responds {ok:true} either way, so an attacker can't tell who's a member.
    - Codes hashed at rest (sha256 salted with tenant+phone), constant-time
      compared, 10-min TTL, 5 attempts then dead.
    - Rate limited per phone+tenant (1/min, 3/hour) to contain SMS cost/abuse,
      counted durably from the DB.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import structlog

from app.db import customers, otp_codes
from app.errors import ExpiredError, InvalidCodeError, RateLimitError
from app.services import twilio_sms_client

log = structlog.get_logger(__name__)

CODE_LENGTH = 4
OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
SEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 3


def _hash_code(tenant_id: str, phone: str, code: str) -> str:
    """Salt the hash with tenant+phone so identical codes for different
    customers never share a hash (and a leaked hash isn't a global rainbow
    target). Short-lived + attempt-limited, so sha256 is sufficient here."""
    return hashlib.sha256(f"{tenant_id}:{phone}:{code}".encode()).hexdigest()


def request_code(*, tenant_id: str, phone: str, now: datetime | None = None) -> None:
    """Send a 4-digit SMS code IF this phone is a customer of the tenant.

    Always returns silently — the endpoint responds {ok:true} regardless, so
    the caller can't enumerate members. Rate-limited per phone+tenant.
    """
    current = now or datetime.now(UTC)

    # Per phone+tenant cooldown + hourly cap (durable, counted from the DB).
    cooldown_start = current - timedelta(seconds=SEND_COOLDOWN_SECONDS)
    if otp_codes.count_since(tenant_id, phone, cooldown_start) >= 1:
        return
    if otp_codes.count_since(tenant_id, phone, current - timedelta(hours=1)) >= MAX_SENDS_PER_HOUR:
        return

    customer = customers.get_by_phone(tenant_id, phone)
    if customer is None:
        # Unknown phone — no row, no SMS, no cost. Anti-enumeration: the
        # endpoint still responds {ok:true}.
        return

    code = f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"
    otp_codes.create(
        tenant_id=tenant_id,
        phone=phone,
        code_hash=_hash_code(tenant_id, phone, code),
        expires_at=current + timedelta(minutes=OTP_TTL_MINUTES),
    )
    twilio_sms_client.send_sms(
        to=phone,
        body=(
            f"Your SmartTap code is {code}. "
            f"It expires in {OTP_TTL_MINUTES} minutes."
        ),
    )


def verify_code(
    *, tenant_id: str, phone: str, code: str, now: datetime | None = None
) -> str:
    """Validate the code and return the customer's magic_link_token on success.

    Raises InvalidCodeError (no/bad code), ExpiredError (TTL passed), or
    RateLimitError (attempts exhausted). A non-customer phone has no code, so
    it fails the same way a wrong code does — no enumeration oracle on verify.
    """
    current = now or datetime.now(UTC)
    otp = otp_codes.get_latest(tenant_id, phone)
    if otp is None or otp.get("consumed_at"):
        raise InvalidCodeError("Invalid or expired code")

    expires = otp.get("expires_at")
    if isinstance(expires, str):
        if datetime.fromisoformat(expires.replace("Z", "+00:00")) <= current:
            raise ExpiredError("Code expired")

    if int(otp.get("attempts") or 0) >= MAX_OTP_ATTEMPTS:
        raise RateLimitError("Too many attempts. Request a new code.")

    if hmac.compare_digest(
        str(otp.get("code_hash") or ""), _hash_code(tenant_id, phone, code)
    ):
        otp_codes.consume(str(otp["id"]), current)
        customer = customers.get_by_phone(tenant_id, phone)
        if customer is None:
            # Customer removed between request and verify — treat as invalid.
            raise InvalidCodeError("Invalid or expired code")
        return str(customer["magic_link_token"])

    attempts = otp_codes.increment_attempts(str(otp["id"]))
    if attempts >= MAX_OTP_ATTEMPTS:
        raise RateLimitError("Too many attempts. Request a new code.")
    raise InvalidCodeError("Invalid code")
