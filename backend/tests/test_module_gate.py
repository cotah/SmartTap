"""Tests for the enabled_modules gate on public loyalty endpoints.

A reviews-only tenant (e.g. enabled_modules=["reviews"]) must not expose the
loyalty surface at all: taps, opt-in identify, OTP re-identification and the
public reward redeem must 404 as if they didn't exist. 404 (not 403) on
purpose — don't reveal that the feature exists but is switched off.

Also covers the per-IP rate limit on POST /v1/taps (the last public endpoint
without one).
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import nfc_tags, rewards, tenants
from app.errors import NotFoundError
from app.main import app
from app.services import otp_service, rate_limit
from app.services.customer_service import IdentifyContext, identify_customer
from app.services.modules import require_module
from app.services.reward_service import validate_and_redeem
from app.services.tap_service import TapContext, process_tap

TENANT = "t-1"
PHONE = "+353871234567"

REVIEWS_ONLY = {"id": TENANT, "is_active": True, "enabled_modules": ["reviews"]}
WITH_LOYALTY = {
    "id": TENANT,
    "is_active": True,
    "enabled_modules": ["loyalty", "reviews"],
}


# --- require_module unit ----------------------------------------------------


def test_require_module_passes_when_enabled() -> None:
    require_module(WITH_LOYALTY, "loyalty")  # no raise


def test_require_module_raises_404_when_disabled() -> None:
    with pytest.raises(NotFoundError):
        require_module(REVIEWS_ONLY, "loyalty")


def test_require_module_defaults_to_both_when_column_missing() -> None:
    # Pre-migration-018 rows (or mocks) without the key keep working.
    require_module({"id": TENANT, "is_active": True}, "loyalty")
    require_module({"id": TENANT, "is_active": True, "enabled_modules": None}, "loyalty")


# --- identify ---------------------------------------------------------------


def _identify_ctx() -> IdentifyContext:
    return IdentifyContext(
        tenant_id=TENANT,
        phone=PHONE,
        name="Ana",
        email=None,
        birthday=None,
        gdpr_consent=True,
        gdpr_consent_text="I agree",
    )


def test_identify_raises_404_for_reviews_only_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: REVIEWS_ONLY)
    with pytest.raises(NotFoundError):
        identify_customer(_identify_ctx())


# --- taps -------------------------------------------------------------------


def _tap_ctx() -> TapContext:
    return TapContext(
        tag_uuid="tag-uuid",
        device_type="ios",
        interaction_type="nfc",
        magic_link_token=None,
        user_agent=None,
        ip=None,
    )


def test_process_tap_raises_404_for_reviews_only_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tag = {"id": "tag-1", "tenant_id": TENANT, "is_active": True}
    monkeypatch.setattr(nfc_tags, "get_by_tag_uuid", lambda _u: tag)
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: REVIEWS_ONLY)
    with pytest.raises(NotFoundError):
        process_tap(_tap_ctx())


# --- OTP --------------------------------------------------------------------


@pytest.fixture()
def _twilio_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """The module-gate tests below must reach the enabled_modules check, so
    let them through the earlier Twilio-configured gate."""
    monkeypatch.setattr(
        otp_service.twilio_sms_client, "is_configured", lambda: True
    )


@pytest.mark.usefixtures("_twilio_on")
def test_otp_request_raises_404_for_reviews_only_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: REVIEWS_ONLY)
    with pytest.raises(NotFoundError):
        otp_service.request_code(tenant_id=TENANT, phone=PHONE)


@pytest.mark.usefixtures("_twilio_on")
def test_otp_request_raises_404_for_unknown_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: None)
    with pytest.raises(NotFoundError):
        otp_service.request_code(tenant_id=TENANT, phone=PHONE)


@pytest.mark.usefixtures("_twilio_on")
def test_otp_verify_raises_404_for_reviews_only_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: REVIEWS_ONLY)
    with pytest.raises(NotFoundError):
        otp_service.verify_code(tenant_id=TENANT, phone=PHONE, code="1234")


def test_otp_request_raises_404_when_twilio_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No Twilio credentials → the OTP surface doesn't exist, even for a
    loyalty tenant. Must 404 before touching the tenant or sending anything."""
    monkeypatch.setattr(
        otp_service.twilio_sms_client, "is_configured", lambda: False
    )
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: WITH_LOYALTY)
    with pytest.raises(NotFoundError):
        otp_service.request_code(tenant_id=TENANT, phone=PHONE)


def test_otp_verify_raises_404_when_twilio_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        otp_service.twilio_sms_client, "is_configured", lambda: False
    )
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: WITH_LOYALTY)
    with pytest.raises(NotFoundError):
        otp_service.verify_code(tenant_id=TENANT, phone=PHONE, code="1234")


# --- public reward redeem ---------------------------------------------------


def test_public_redeem_raises_404_for_reviews_only_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reward: dict[str, Any] = {
        "id": "rw-1",
        "tenant_id": TENANT,
        "customer_id": "cust-1",
        "validation_code": "123456",
        "redeemed_at": None,
        "expires_at": datetime.now(UTC).isoformat(),
    }
    monkeypatch.setattr(rewards, "get_by_id", lambda _r: reward)
    monkeypatch.setattr(tenants, "get_by_id", lambda _t: REVIEWS_ONLY)
    with pytest.raises(NotFoundError):
        validate_and_redeem(
            reward_id="rw-1", validation_code="123456", redeemed_by_user=None
        )


# --- tap rate limit ---------------------------------------------------------


def test_tap_endpoint_rate_limited_at_30_per_minute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rate_limit.reset()
    from app.routers import taps as taps_router

    def fake_process_tap(_ctx: TapContext) -> None:
        raise NotFoundError("Tag not found")

    monkeypatch.setattr(taps_router, "process_tap", fake_process_tap)
    client = TestClient(app)

    for _ in range(30):
        r = client.post("/v1/taps/some-uuid", json={})
        assert r.status_code == 404
    r = client.post("/v1/taps/some-uuid", json={})
    assert r.status_code == 429
    rate_limit.reset()
