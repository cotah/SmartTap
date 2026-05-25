from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import tenant_service
from app.services.tenant_service import RewardConfig, get_self, update_reward_config


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
