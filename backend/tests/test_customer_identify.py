"""Tests for the public opt-in identify flow.

Security-critical: /v1/customers/identify is unauthenticated. It may mint a
session token for a NEW customer (that's signup), but it must NEVER return
the stored magic_link_token of an existing customer — phone number alone is
not proof of possession (account takeover). Existing phones get a 409.
"""

from datetime import date
from typing import Any

import pytest

from app.errors import AlreadyRegisteredError, InactiveError, NotFoundError
from app.services import customer_service as svc
from app.services.customer_service import IdentifyContext, identify_customer

TENANT = "t-1"
PHONE = "+353871234567"


def _ctx(**overrides: Any) -> IdentifyContext:
    defaults: dict[str, Any] = {
        "tenant_id": TENANT,
        "phone": PHONE,
        "name": "Ana",
        "email": None,
        "birthday": None,
        "gdpr_consent": True,
        "gdpr_consent_text": "I agree",
    }
    defaults.update(overrides)
    return IdentifyContext(**defaults)


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant: dict[str, Any] | None,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    captured: dict[str, Any] = {"created_with": None}

    def fake_create(**kwargs: Any) -> dict[str, Any]:
        captured["created_with"] = kwargs
        return {
            "id": "cust-new",
            "magic_link_token": "tok-new",
            "current_stamps": 0,
        }

    monkeypatch.setattr(svc.tenants, "get_by_id", lambda _t: tenant)
    monkeypatch.setattr(svc.customers, "get_by_phone", lambda _t, _p: existing)
    monkeypatch.setattr(svc.customers, "create", fake_create)
    return captured


ACTIVE_TENANT = {"id": TENANT, "is_active": True}


def test_new_phone_creates_customer_and_returns_fresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch(monkeypatch, tenant=ACTIVE_TENANT, existing=None)

    result = identify_customer(_ctx(birthday=date(1990, 5, 1)))

    assert result.is_new is True
    assert result.customer_id == "cust-new"
    assert result.magic_link_token == "tok-new"
    assert result.stamps_current == 0
    assert captured["created_with"]["phone"] == PHONE
    assert captured["created_with"]["birthday"] == "1990-05-01"


def test_existing_phone_raises_conflict_and_never_leaks_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = {
        "id": "cust-1",
        "magic_link_token": "tok-secret",
        "current_stamps": 4,
    }
    _patch(monkeypatch, tenant=ACTIVE_TENANT, existing=existing)

    with pytest.raises(AlreadyRegisteredError) as exc:
        identify_customer(_ctx())

    # The stored session token must not ride along anywhere on the error.
    assert "tok-secret" not in str(exc.value)
    assert "tok-secret" not in str(exc.value.detail)


def test_unknown_tenant_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, tenant=None, existing=None)
    with pytest.raises(NotFoundError):
        identify_customer(_ctx())


def test_inactive_tenant_raises_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, tenant={"id": TENANT, "is_active": False}, existing=None)
    with pytest.raises(InactiveError):
        identify_customer(_ctx())
