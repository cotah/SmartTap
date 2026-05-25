from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.services.trial_service import (
    EXPIRING_SOON_DAYS,
    compute_trial_status,
    is_blocking,
)


def _tenant(
    *,
    plan: str = "trial",
    is_active: bool = True,
    trial_ends_at: datetime | str | None = None,
) -> dict[str, Any]:
    return {
        "plan": plan,
        "is_active": is_active,
        "trial_ends_at": (
            trial_ends_at.isoformat()
            if isinstance(trial_ends_at, datetime)
            else trial_ends_at
        ),
    }


def test_inactive_subscription_overrides_everything() -> None:
    """Cancelled subscriptions land here regardless of plan; we must report
    inactive so the dependency layer 402s on mutations."""
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = _tenant(
        plan="loyalty",
        is_active=False,
        trial_ends_at=now + timedelta(days=30),
    )
    assert compute_trial_status(tenant, now=now) == "inactive"


def test_paid_plan_is_subscribed() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    assert compute_trial_status(_tenant(plan="loyalty"), now=now) == "subscribed"
    assert compute_trial_status(_tenant(plan="review"), now=now) == "subscribed"
    assert compute_trial_status(_tenant(plan="pro"), now=now) == "subscribed"
    assert compute_trial_status(_tenant(plan="network"), now=now) == "subscribed"


def test_trial_without_end_date_is_active() -> None:
    """Defensive: tenant predating trial_ends_at column shouldn't be locked."""
    assert compute_trial_status(_tenant(trial_ends_at=None)) == "active"


def test_trial_well_within_window_is_active() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = _tenant(trial_ends_at=now + timedelta(days=15))
    assert compute_trial_status(tenant, now=now) == "active"


def test_trial_within_expiring_window_is_expiring_soon() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    # 5 days left → inside the 7-day window
    tenant = _tenant(trial_ends_at=now + timedelta(days=5))
    assert compute_trial_status(tenant, now=now) == "expiring_soon"


def test_trial_at_boundary_is_expiring_soon() -> None:
    """Exactly EXPIRING_SOON_DAYS away should still trigger the amber state."""
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = _tenant(trial_ends_at=now + timedelta(days=EXPIRING_SOON_DAYS))
    assert compute_trial_status(tenant, now=now) == "expiring_soon"


def test_trial_past_end_is_expired() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = _tenant(trial_ends_at=now - timedelta(seconds=1))
    assert compute_trial_status(tenant, now=now) == "expired"


def test_trial_exactly_at_end_is_expired() -> None:
    """now == ends should be expired (not active) — the user got their full
    30 days; the day-of, mutations stop."""
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = _tenant(trial_ends_at=now)
    assert compute_trial_status(tenant, now=now) == "expired"


def test_handles_naive_datetime_string_from_db() -> None:
    """Sometimes the DB returns ISO without offset; we must not crash and
    must not silently mis-compare to a UTC-aware `now`."""
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = {
        "plan": "trial",
        "is_active": True,
        # No timezone in the string — coerced to UTC by the parser.
        "trial_ends_at": "2026-06-25T00:00:00",
    }
    assert compute_trial_status(tenant, now=now) == "active"


def test_handles_z_suffix_iso_string() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    tenant = {
        "plan": "trial",
        "is_active": True,
        "trial_ends_at": "2026-06-25T00:00:00Z",
    }
    assert compute_trial_status(tenant, now=now) == "active"


def test_handles_malformed_iso_as_no_date() -> None:
    """Garbage input must not raise — fall back to active (don't lock out)."""
    tenant = {"plan": "trial", "is_active": True, "trial_ends_at": "not-a-date"}
    assert compute_trial_status(tenant) == "active"


@pytest.mark.parametrize(
    "status,expected",
    [
        ("active", False),
        ("expiring_soon", False),
        ("subscribed", False),
        ("expired", True),
        ("inactive", True),
    ],
)
def test_is_blocking_matrix(status: str, expected: bool) -> None:
    assert is_blocking(status) is expected  # type: ignore[arg-type]
