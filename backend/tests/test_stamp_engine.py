from datetime import UTC, datetime, timedelta

from app.services.stamp_engine import (
    can_award_stamp,
    compute_reward_state,
    generate_validation_code,
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
