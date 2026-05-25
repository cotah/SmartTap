from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import tenant_service
from app.services.tenant_service import (
    RewardConfig,
    TenantSettings,
    get_self,
    update_reward_config,
    update_settings,
)


def _empty_settings(**over: Any) -> TenantSettings:
    base: dict[str, Any] = {
        "name": None,
        "logo_url": None,
        "primary_color": None,
        "accent_color": None,
        "google_place_id": None,
        "google_review_url": None,
        "google_business_url": None,
    }
    base.update(over)
    return TenantSettings(**base)


def test_get_self_returns_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    row: dict[str, Any] = {"id": "t-1", "name": "ACME Barber"}
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: row)
    assert get_self("t-1") == row


def test_get_self_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: None)
    with pytest.raises(NotFoundError):
        get_self("missing")


def test_update_reward_config_writes_expected_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        tenant_service.tenants, "get_by_id", lambda _id: {"id": "t-1"}
    )

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        captured["tenant_id"] = tenant_id
        captured["fields"] = fields
        return {"id": tenant_id, **fields}

    monkeypatch.setattr(tenant_service.tenants, "update", fake_update)

    update_reward_config(
        "t-1",
        RewardConfig(
            stamps_for_reward=8,
            reward_description="  Free haircut  ",
            reward_expires_days=45,
            stamp_rate_limit_minutes=90,
        ),
    )

    assert captured["tenant_id"] == "t-1"
    assert captured["fields"] == {
        "stamps_for_reward": 8,
        "reward_description": "Free haircut",  # trimmed
        "reward_expires_days": 45,
        "stamp_rate_limit_minutes": 90,
    }


def test_update_reward_config_raises_when_tenant_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: None)

    with pytest.raises(NotFoundError):
        update_reward_config(
            "missing",
            RewardConfig(
                stamps_for_reward=8,
                reward_description="Free haircut",
                reward_expires_days=45,
                stamp_rate_limit_minutes=90,
            ),
        )


def test_update_settings_updates_only_provided_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: {"id": "t-1"})

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        captured["tenant_id"] = tenant_id
        captured["fields"] = fields
        return {"id": tenant_id, **fields}

    monkeypatch.setattr(tenant_service.tenants, "update", fake_update)

    update_settings(
        "t-1",
        _empty_settings(
            name="  ACME Barber  ",
            primary_color="#112233",
            google_review_url="https://g.page/r/acme",
        ),
    )

    assert captured["fields"] == {
        "name": "ACME Barber",  # trimmed
        "primary_color": "#112233",
        "google_review_url": "https://g.page/r/acme",
    }
    # Untouched fields stay out of the update payload entirely.
    assert "logo_url" not in captured["fields"]
    assert "google_business_url" not in captured["fields"]


def test_update_settings_empty_string_clears_nullable_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: {"id": "t-1"})

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        captured["fields"] = fields
        return {"id": tenant_id, **fields}

    monkeypatch.setattr(tenant_service.tenants, "update", fake_update)

    update_settings("t-1", _empty_settings(logo_url="", google_review_url=""))

    assert captured["fields"] == {"logo_url": None, "google_review_url": None}


def test_update_settings_noop_returns_existing_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = {"id": "t-1", "name": "Old"}
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: existing)

    def fail_update(*_: Any, **__: Any) -> None:
        raise AssertionError("update should not be called for empty payload")

    monkeypatch.setattr(tenant_service.tenants, "update", fail_update)

    result = update_settings("t-1", _empty_settings())
    assert result is existing


def test_update_settings_raises_when_tenant_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tenant_service.tenants, "get_by_id", lambda _id: None)
    with pytest.raises(NotFoundError):
        update_settings("missing", _empty_settings(name="Whatever"))
