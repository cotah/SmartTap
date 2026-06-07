"""Tests for the customer phone OTP service (Sprint 5.6).

The risky surface is all here: anti-enumeration (never reveal who's a
customer), rate limiting (SMS costs money), constant-time verification, TTL,
and attempt lockout. The db + SMS client are stubbed so each rule is exercised
in isolation.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.errors import ExpiredError, InvalidCodeError, RateLimitError
from app.services import otp_service as svc

NOW = datetime(2026, 6, 7, 12, 0, tzinfo=UTC)
TENANT = "t-1"
PHONE = "+353871234567"


# ---------------------------------------------------------------------------
# request_code
# ---------------------------------------------------------------------------


def _patch_request(
    monkeypatch: pytest.MonkeyPatch,
    *,
    customer: dict[str, Any] | None,
    counts: list[int] | None = None,
) -> dict[str, Any]:
    """Wire request_code's collaborators. `counts` feeds successive
    count_since() returns (cooldown check, then hourly check)."""
    captured: dict[str, Any] = {"created": None, "sent": None}
    count_iter = iter(counts or [0, 0])

    monkeypatch.setattr(svc.otp_codes, "count_since", lambda *a, **k: next(count_iter))
    monkeypatch.setattr(svc.customers, "get_by_phone", lambda _t, _p: customer)

    def fake_create(**kwargs: Any) -> dict[str, Any]:
        captured["created"] = kwargs
        return {"id": "otp-1", **kwargs}

    def fake_send(**kwargs: Any) -> str:
        captured["sent"] = kwargs
        return "SMxxx"

    monkeypatch.setattr(svc.otp_codes, "create", fake_create)
    monkeypatch.setattr(svc.twilio_sms_client, "send_sms", fake_send)
    return captured


def test_request_code_sends_4_digit_code_to_a_real_customer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _patch_request(monkeypatch, customer={"id": "c-1", "magic_link_token": "tok"})

    svc.request_code(tenant_id=TENANT, phone=PHONE, now=NOW)

    assert cap["created"] is not None
    assert cap["sent"] is not None
    # The SMS body carries a 4-digit code...
    match = re.search(r"\b(\d{4})\b", cap["sent"]["body"])
    assert match is not None
    code = match.group(1)
    # ...and the stored hash matches that exact code (salted with tenant+phone).
    assert cap["created"]["code_hash"] == svc._hash_code(TENANT, PHONE, code)
    assert cap["sent"]["to"] == PHONE


def test_request_code_unknown_phone_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-enumeration: a non-customer triggers no row and no SMS (no cost),
    yet the endpoint still answers ok — the caller can't tell the difference."""
    cap = _patch_request(monkeypatch, customer=None)

    svc.request_code(tenant_id=TENANT, phone=PHONE, now=NOW)

    assert cap["created"] is None
    assert cap["sent"] is None


def test_request_code_respects_per_minute_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A code already created within the last 60s → skip silently.
    cap = _patch_request(
        monkeypatch, customer={"id": "c-1", "magic_link_token": "t"}, counts=[1, 0]
    )
    svc.request_code(tenant_id=TENANT, phone=PHONE, now=NOW)
    assert cap["sent"] is None


def test_request_code_respects_hourly_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    # Cooldown clear (0) but 3 sends already this hour → skip silently.
    cap = _patch_request(
        monkeypatch, customer={"id": "c-1", "magic_link_token": "t"}, counts=[0, 3]
    )
    svc.request_code(tenant_id=TENANT, phone=PHONE, now=NOW)
    assert cap["sent"] is None


# ---------------------------------------------------------------------------
# verify_code
# ---------------------------------------------------------------------------


def _otp_row(**over: Any) -> dict[str, Any]:
    base = {
        "id": "otp-1",
        "code_hash": svc._hash_code(TENANT, PHONE, "1234"),
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "attempts": 0,
        "consumed_at": None,
    }
    base.update(over)
    return base


def _patch_verify(
    monkeypatch: pytest.MonkeyPatch,
    *,
    otp: dict[str, Any] | None,
    customer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    captured: dict[str, Any] = {"consumed": False, "attempts_bumped": 0}
    monkeypatch.setattr(svc.otp_codes, "get_latest", lambda _t, _p: otp)
    monkeypatch.setattr(
        svc.customers,
        "get_by_phone",
        lambda _t, _p: customer or {"id": "c-1", "magic_link_token": "tok-abc"},
    )

    def fake_consume(_id: str, _at: datetime) -> None:
        captured["consumed"] = True

    def fake_increment(_id: str) -> int:
        captured["attempts_bumped"] += 1
        return int(otp.get("attempts", 0)) + 1 if otp else 1

    monkeypatch.setattr(svc.otp_codes, "consume", fake_consume)
    monkeypatch.setattr(svc.otp_codes, "increment_attempts", fake_increment)
    return captured


def test_verify_correct_code_consumes_and_returns_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _patch_verify(monkeypatch, otp=_otp_row())
    token = svc.verify_code(tenant_id=TENANT, phone=PHONE, code="1234", now=NOW)
    assert token == "tok-abc"
    assert cap["consumed"] is True


def test_verify_wrong_code_bumps_attempts_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _patch_verify(monkeypatch, otp=_otp_row())
    with pytest.raises(InvalidCodeError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="9999", now=NOW)
    assert cap["attempts_bumped"] == 1


def test_verify_expired_code_raises_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_verify(
        monkeypatch, otp=_otp_row(expires_at=(NOW - timedelta(minutes=1)).isoformat())
    )
    with pytest.raises(ExpiredError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="1234", now=NOW)


def test_verify_exhausted_attempts_raises_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_verify(monkeypatch, otp=_otp_row(attempts=5))
    with pytest.raises(RateLimitError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="1234", now=NOW)


def test_verify_no_code_raises_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_verify(monkeypatch, otp=None)
    with pytest.raises(InvalidCodeError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="1234", now=NOW)


def test_verify_consumed_code_raises_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_verify(monkeypatch, otp=_otp_row(consumed_at=NOW.isoformat()))
    with pytest.raises(InvalidCodeError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="1234", now=NOW)


def test_verify_wrong_code_on_final_attempt_raises_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4 prior attempts; a 5th wrong one tips into lockout (RateLimitError)."""
    _patch_verify(monkeypatch, otp=_otp_row(attempts=4))
    with pytest.raises(RateLimitError):
        svc.verify_code(tenant_id=TENANT, phone=PHONE, code="9999", now=NOW)
