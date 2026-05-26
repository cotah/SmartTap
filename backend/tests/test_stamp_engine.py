from datetime import UTC, datetime, timedelta

import pytest

from app.services.stamp_engine import (
    MAX_MULTIPLIER,
    MIN_MULTIPLIER,
    can_award_stamp,
    compute_reward_state,
    generate_validation_code,
    multiplier_for_campaign,
    reward_expiry,
)


def test_can_award_stamp_first_time() -> None:
    assert can_award_stamp(None, 120, datetime.now(UTC)) is True


def test_can_award_stamp_within_window_blocks() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    last = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
    assert can_award_stamp(last, 120, now) is False


def test_can_award_stamp_after_window() -> None:
    now = datetime(2026, 1, 1, 14, 0, tzinfo=UTC)
    last = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
    assert can_award_stamp(last, 120, now) is True


def test_can_award_stamp_zero_rate_limit_always_allows() -> None:
    now = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)
    last = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert can_award_stamp(last, 0, now) is True


def test_compute_reward_state_empty() -> None:
    s = compute_reward_state(0, 10)
    assert s.progress_percent == 0
    assert s.stamps_remaining == 10
    assert s.reward_ready is False


def test_compute_reward_state_complete() -> None:
    s = compute_reward_state(10, 10)
    assert s.progress_percent == 100
    assert s.stamps_remaining == 0
    assert s.reward_ready is True


def test_compute_reward_state_caps_at_100() -> None:
    s = compute_reward_state(15, 10)
    assert s.progress_percent == 100
    assert s.reward_ready is True


def test_compute_reward_state_zero_threshold_safe() -> None:
    s = compute_reward_state(5, 0)
    assert s.progress_percent == 0
    assert s.reward_ready is False


def test_generate_validation_code_format() -> None:
    code = generate_validation_code()
    assert len(code) == 6
    assert code.isdigit()


def test_reward_expiry_returns_future_datetime() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    expiry = reward_expiry(now, 30)
    assert expiry == now + timedelta(days=30)


# ---------------------------------------------------------------------------
# multiplier_for_campaign
# ---------------------------------------------------------------------------


def test_multiplier_for_none_campaign_is_one() -> None:
    assert multiplier_for_campaign(None) == 1


def test_multiplier_for_non_double_stamp_is_one() -> None:
    """birthday / reactivation / custom don't multiply stamps; that's a
    behaviour exclusive to double_stamp."""
    assert (
        multiplier_for_campaign({"type": "birthday", "config": {"multiplier": 5}}) == 1
    )


@pytest.mark.parametrize("value,expected", [(2, 2), (3, 3), (5, 5)])
def test_multiplier_within_range_is_returned_as_is(value: int, expected: int) -> None:
    assert (
        multiplier_for_campaign(
            {"type": "double_stamp", "config": {"multiplier": value}}
        )
        == expected
    )


@pytest.mark.parametrize("value", [-1, 0, 1])
def test_multiplier_below_min_clamps_to_min(value: int) -> None:
    assert (
        multiplier_for_campaign(
            {"type": "double_stamp", "config": {"multiplier": value}}
        )
        == MIN_MULTIPLIER
    )


@pytest.mark.parametrize("value", [6, 10, 9999])
def test_multiplier_above_max_clamps_to_max(value: int) -> None:
    assert (
        multiplier_for_campaign(
            {"type": "double_stamp", "config": {"multiplier": value}}
        )
        == MAX_MULTIPLIER
    )


@pytest.mark.parametrize("bad", [{"multiplier": "banana"}, {}, None, "not-a-dict"])
def test_multiplier_with_malformed_config_falls_back_to_min(bad: object) -> None:
    """Corrupt config must not block stamp awarding. MIN is the safe floor:
    we'd rather give the customer a small bonus than crash on a tap."""
    assert (
        multiplier_for_campaign({"type": "double_stamp", "config": bad}) == MIN_MULTIPLIER
    )
