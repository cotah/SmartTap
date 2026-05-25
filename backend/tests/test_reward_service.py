from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.errors import AlreadyRedeemedError, ExpiredError, InvalidCodeError
from app.services import reward_service
from app.services.reward_service import validate_and_redeem_by_code


def _reward(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "r-1",
        "tenant_id": "t-1",
        "customer_id": "c-1",
        "validation_code": "123456",
        "description": "Free haircut",
        "redeemed_at": None,
        "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    }
    base.update(over)
    return base


def test_validate_by_code_redeems_active_reward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reward = _reward()
    redeem_calls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(
        reward_service.rewards,
        "get_by_validation_code",
        lambda tenant_id, code: reward if (tenant_id, code) == ("t-1", "123456") else None,
    )

    def fake_redeem(reward_id: str, user_id: str | None) -> dict[str, Any]:
        redeem_calls.append((reward_id, user_id))
        return {**reward, "redeemed_at": "2026-05-25T12:00:00+00:00"}

    monkeypatch.setattr(reward_service.rewards, "redeem", fake_redeem)
    monkeypatch.setattr(
        reward_service.customers, "get_by_id", lambda _id: {"id": "c-1", "name": "Alice"}
    )

    result = validate_and_redeem_by_code(
        tenant_id="t-1",
        validation_code="123456",
        redeemed_by_user="user-1",
    )

    assert redeem_calls == [("r-1", "user-1")]
    assert result.reward_id == "r-1"
    assert result.customer_id == "c-1"
    assert result.customer_name == "Alice"
    assert result.description == "Free haircut"


def test_validate_by_code_unknown_code_returns_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reward_service.rewards, "get_by_validation_code", lambda *_: None
    )
    with pytest.raises(InvalidCodeError):
        validate_and_redeem_by_code(
            tenant_id="t-1", validation_code="999999", redeemed_by_user=None
        )


def test_validate_by_code_blocks_already_redeemed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reward_service.rewards,
        "get_by_validation_code",
        lambda *_: _reward(redeemed_at="2026-04-01T10:00:00+00:00"),
    )
    with pytest.raises(AlreadyRedeemedError):
        validate_and_redeem_by_code(
            tenant_id="t-1", validation_code="123456", redeemed_by_user=None
        )


def test_validate_by_code_blocks_expired_reward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    monkeypatch.setattr(
        reward_service.rewards,
        "get_by_validation_code",
        lambda *_: _reward(expires_at=past),
    )
    with pytest.raises(ExpiredError):
        validate_and_redeem_by_code(
            tenant_id="t-1", validation_code="123456", redeemed_by_user=None
        )


def test_validate_by_code_is_tenant_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A code that exists in tenant A must not be redeemable while authenticated
    as tenant B — the DB lookup is the gate."""
    captured: dict[str, Any] = {}

    def fake_lookup(tenant_id: str, code: str) -> None:
        captured["tenant_id"] = tenant_id
        captured["code"] = code
        return None

    monkeypatch.setattr(reward_service.rewards, "get_by_validation_code", fake_lookup)
    with pytest.raises(InvalidCodeError):
        validate_and_redeem_by_code(
            tenant_id="tenant-B",
            validation_code="123456",
            redeemed_by_user="user-from-B",
        )
    assert captured == {"tenant_id": "tenant-B", "code": "123456"}
