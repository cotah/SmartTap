"""Integration tests for process_tap interacting with double_stamp campaigns.

Focuses on the multiplier math — that current_stamps moves by N during a
campaign, doesn't move outside the window, and that crossing the reward
threshold with a multiplied stamp leaves the correct remainder.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.services import tap_service
from app.services.tap_service import TapContext, process_tap

NOW = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Heavy-but-localised stubs — process_tap touches 7 DB modules
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _freeze_now(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin datetime.now(UTC) inside tap_service so reward expiry and rate
    limit math are deterministic. Other modules read their own datetime."""

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return NOW if tz is None else NOW.astimezone(tz)

    monkeypatch.setattr(tap_service, "datetime", _FixedDatetime)


def _wire(
    monkeypatch: pytest.MonkeyPatch,
    *,
    customer: dict[str, Any],
    tenant_overrides: dict[str, Any] | None = None,
    active_campaign: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replace every DB the tap_service touches. Returns the customer dict
    so tests can read its mutated state after process_tap."""
    tag = {"id": "tag-1", "tenant_id": "t-1", "is_active": True}
    tenant = {
        "id": "t-1",
        "is_active": True,
        "stamp_rate_limit_minutes": 0,
        "stamps_for_reward": 10,
        "reward_description": "Free haircut",
        "reward_expires_days": 30,
    }
    if tenant_overrides:
        tenant.update(tenant_overrides)

    monkeypatch.setattr(
        tap_service.nfc_tags, "get_by_tag_uuid", lambda _u: dict(tag)
    )
    monkeypatch.setattr(tap_service.tenants, "get_by_id", lambda _t: dict(tenant))
    monkeypatch.setattr(
        tap_service.customers,
        "get_by_magic_token",
        lambda _t: dict(customer),
    )

    def fake_update(cid: str, fields: dict[str, Any]) -> dict[str, Any]:
        customer.update(fields)
        return dict(customer)

    monkeypatch.setattr(tap_service.customers, "update", fake_update)

    monkeypatch.setattr(
        tap_service.taps,
        "create",
        lambda **_kw: {"id": "tap-1"},
    )
    # No prior stamp — rate limit doesn't kick in.
    monkeypatch.setattr(tap_service.stamps, "last_for_customer", lambda _c: None)

    created_stamps: list[dict[str, Any]] = []

    def fake_stamps_create(**kwargs: Any) -> dict[str, Any]:
        row = {"id": f"st-{len(created_stamps) + 1}", **kwargs}
        created_stamps.append(row)
        return row

    monkeypatch.setattr(tap_service.stamps, "create", fake_stamps_create)

    created_rewards: list[dict[str, Any]] = []

    def fake_rewards_create(**kwargs: Any) -> dict[str, Any]:
        row = {"id": f"rw-{len(created_rewards) + 1}", **kwargs}
        created_rewards.append(row)
        return row

    monkeypatch.setattr(tap_service.rewards, "create", fake_rewards_create)
    monkeypatch.setattr(tap_service.rewards, "get_active_for_customer", lambda _c: None)

    # The campaign lookup the new code performs.
    monkeypatch.setattr(
        tap_service.campaign_service,
        "find_active_for_tap",
        lambda _tid, now=None: active_campaign,
    )

    return {"customer": customer, "stamps": created_stamps, "rewards": created_rewards}


def _ctx() -> TapContext:
    return TapContext(
        tag_uuid="abc",
        device_type="ios",
        interaction_type="nfc",
        magic_link_token="mlt-1",
        user_agent="ua",
        ip="1.2.3.4",
    )


def _customer(current: int = 0) -> dict[str, Any]:
    return {
        "id": "c-1",
        "tenant_id": "t-1",
        "name": "Alice",
        "current_stamps": current,
        "total_stamps": 0,
        "total_visits": 0,
        "last_visit_at": None,
    }


# ---------------------------------------------------------------------------
# No campaign — current behaviour preserved
# ---------------------------------------------------------------------------


def test_tap_without_campaign_awards_one_stamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _wire(monkeypatch, customer=_customer(current=3), active_campaign=None)
    result = process_tap(_ctx())

    assert result.stamp_awarded is True
    assert result.stamps_awarded_count == 1
    assert result.active_campaign is None
    assert state["customer"]["current_stamps"] == 4
    assert state["stamps"][0]["multiplier"] == 1


# ---------------------------------------------------------------------------
# With campaign — multiplier applied
# ---------------------------------------------------------------------------


def _campaign(multiplier: int) -> dict[str, Any]:
    return {
        "id": "camp-1",
        "name": "Weekend boost",
        "type": "double_stamp",
        "status": "active",
        "config": {"multiplier": multiplier},
        "starts_at": (NOW - timedelta(days=1)).isoformat(),
        "ends_at": (NOW + timedelta(days=1)).isoformat(),
    }


def test_tap_during_2x_campaign_awards_two_stamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _wire(
        monkeypatch,
        customer=_customer(current=3),
        active_campaign=_campaign(multiplier=2),
    )
    result = process_tap(_ctx())

    assert result.stamps_awarded_count == 2
    assert state["customer"]["current_stamps"] == 5
    # The stamp row records the multiplier for audit / future reporting.
    assert state["stamps"][0]["multiplier"] == 2
    assert result.active_campaign is not None
    assert result.active_campaign["id"] == "camp-1"


def test_tap_during_3x_campaign_awards_three_stamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _wire(
        monkeypatch,
        customer=_customer(current=0),
        active_campaign=_campaign(multiplier=3),
    )
    process_tap(_ctx())

    assert state["customer"]["current_stamps"] == 3
    assert state["stamps"][0]["multiplier"] == 3


def test_tap_crossing_threshold_with_multiplier_leaves_remainder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """current=9, threshold=10, multiplier=2 → fire reward, leave 1 stamp.
    The remainder rule prevents the customer from feeling like they wasted
    the bonus stamp."""
    state = _wire(
        monkeypatch,
        customer=_customer(current=9),
        active_campaign=_campaign(multiplier=2),
    )
    result = process_tap(_ctx())

    assert result.reward_available is not None
    # 9 + 2 = 11; 11 - 10 = 1 leftover stamp
    assert state["customer"]["current_stamps"] == 1
    assert len(state["rewards"]) == 1


def test_tap_crossing_threshold_exact_with_multiplier_resets_to_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _wire(
        monkeypatch,
        customer=_customer(current=8),
        active_campaign=_campaign(multiplier=2),
    )
    result = process_tap(_ctx())

    assert result.reward_available is not None
    assert state["customer"]["current_stamps"] == 0


def test_malformed_multiplier_falls_back_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A campaign with config={multiplier: "banana"} is corrupt data, but
    the tap path must still award stamps. multiplier_for_campaign clamps to
    MIN_MULTIPLIER (2) — better to give a bit too much than reject the tap."""
    bad_campaign = _campaign(multiplier=2)
    bad_campaign["config"] = {"multiplier": "banana"}
    state = _wire(
        monkeypatch, customer=_customer(current=0), active_campaign=bad_campaign
    )
    result = process_tap(_ctx())

    assert result.stamps_awarded_count == 2  # MIN_MULTIPLIER fallback
    assert state["customer"]["current_stamps"] == 2


def test_response_carries_active_campaign_for_ui_badge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The customer-facing page renders a "{N}x today" badge from this field.
    Pin the contract — if the field disappears, the badge silently breaks."""
    _wire(
        monkeypatch,
        customer=_customer(current=0),
        active_campaign=_campaign(multiplier=4),
    )
    result = process_tap(_ctx())

    assert result.active_campaign is not None
    assert result.active_campaign["config"]["multiplier"] == 4
