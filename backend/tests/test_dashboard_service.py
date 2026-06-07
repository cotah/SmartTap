"""Tests for the dashboard service additions (Fase B — Dashboard overview).

Two pieces own timezone-sensitive math and are independently risky:

    - `loyalty_visits_today`: "today" is a Dublin calendar day, not UTC. Near
      midnight (and across the March/October DST flips) a UTC-anchored "today"
      counts the wrong taps.
    - `taps_timeseries`: each tap is bucketed by its **Dublin** calendar date,
      empty days are zero-filled, and only stamp/review actions are tallied.
      A tap at 23:30 UTC in summer (IST) belongs to the *next* Dublin day.

These stub the db layer (`taps.count_in_range` / `taps.list_in_range`) so each
behaviour is exercised in isolation.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.services import dashboard_service as svc

# ---------------------------------------------------------------------------
# Dublin day boundaries
# ---------------------------------------------------------------------------


def test_today_bounds_winter_is_exact_utc_midnight() -> None:
    """January Dublin is GMT (UTC+0): the day bounds line up with UTC."""
    now = datetime(2026, 1, 15, 9, 0, tzinfo=UTC)
    start, end = svc._today_bounds_utc(now)
    assert start == datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 1, 16, 0, 0, tzinfo=UTC)


def test_today_bounds_summer_offsets_by_one_hour() -> None:
    """May Dublin is IST (UTC+1): 15 May 00:00 local = 14 May 23:00 UTC."""
    now = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)
    start, end = svc._today_bounds_utc(now)
    assert start == datetime(2026, 5, 14, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 5, 15, 23, 0, tzinfo=UTC)


def test_today_bounds_anchors_in_dublin_not_utc_near_midnight() -> None:
    """14 May 23:30 UTC during IST is already 15 May 00:30 in Dublin, so
    "today" is the 15th — a UTC-anchored impl would say the 14th."""
    now = datetime(2026, 5, 14, 23, 30, tzinfo=UTC)
    start, end = svc._today_bounds_utc(now)
    assert start == datetime(2026, 5, 14, 23, 0, tzinfo=UTC)  # 15 May 00:00 IST
    assert end == datetime(2026, 5, 15, 23, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# loyalty_visits_today
# ---------------------------------------------------------------------------


def test_loyalty_visits_today_counts_only_stamp_earned_today(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def fake_count(
        tenant_id: str, *, start: datetime, end: datetime, action_taken: Any = None
    ) -> int:
        seen["tenant_id"] = tenant_id
        seen["start"] = start
        seen["end"] = end
        seen["action_taken"] = action_taken
        return 7

    monkeypatch.setattr(svc.taps, "count_in_range", fake_count)
    now = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)

    result = svc.loyalty_visits_today("t-1", now=now)

    assert result == 7
    assert seen["action_taken"] == "stamp_earned"
    assert seen["start"] == datetime(2026, 5, 14, 23, 0, tzinfo=UTC)
    assert seen["end"] == datetime(2026, 5, 15, 23, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# taps_timeseries
# ---------------------------------------------------------------------------


def test_timeseries_zero_fills_every_day_in_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: [])
    now = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)

    points = svc.taps_timeseries("t-1", days=30, now=now)

    assert len(points) == 30
    assert points[0].date == "2026-04-16"  # 30 days back, inclusive
    assert points[-1].date == "2026-05-15"  # today (Dublin)
    assert all(p.stamps == 0 and p.reviews == 0 for p in points)


def test_timeseries_buckets_stamps_and_reviews_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"created_at": "2026-05-15T09:00:00+00:00", "action_taken": "stamp_earned"},
        {"created_at": "2026-05-15T10:00:00+00:00", "action_taken": "stamp_earned"},
        {"created_at": "2026-05-15T11:00:00+00:00", "action_taken": "review_clicked"},
        {"created_at": "2026-05-14T09:00:00+00:00", "action_taken": "stamp_earned"},
        # action with no outcome must not inflate either series
        {"created_at": "2026-05-15T12:00:00+00:00", "action_taken": None},
    ]
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: rows)
    now = datetime(2026, 5, 15, 20, 0, tzinfo=UTC)

    points = {p.date: p for p in svc.taps_timeseries("t-1", days=30, now=now)}

    assert points["2026-05-15"].stamps == 2
    assert points["2026-05-15"].reviews == 1
    assert points["2026-05-14"].stamps == 1
    assert points["2026-05-14"].reviews == 0


def test_timeseries_buckets_by_dublin_day_across_dst_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tap at 23:30 UTC on 14 May (IST) is 00:30 on 15 May in Dublin — it
    must land on the 15th, not the 14th."""
    rows = [
        {"created_at": "2026-05-14T23:30:00+00:00", "action_taken": "stamp_earned"},
    ]
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: rows)
    now = datetime(2026, 5, 15, 20, 0, tzinfo=UTC)

    points = {p.date: p for p in svc.taps_timeseries("t-1", days=30, now=now)}

    assert points["2026-05-15"].stamps == 1
    assert points["2026-05-14"].stamps == 0


def test_timeseries_handles_trailing_z_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Some rows may arrive with a 'Z' suffix instead of +00:00."""
    rows = [{"created_at": "2026-05-15T09:00:00Z", "action_taken": "stamp_earned"}]
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: rows)
    now = datetime(2026, 5, 15, 20, 0, tzinfo=UTC)

    points = {p.date: p for p in svc.taps_timeseries("t-1", days=30, now=now)}
    assert points["2026-05-15"].stamps == 1


def test_timeseries_caps_window_at_90_days(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: [])
    now = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)

    points = svc.taps_timeseries("t-1", days=9999, now=now)
    assert len(points) == 90


def test_timeseries_clamps_non_positive_days_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: [])
    now = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)

    points = svc.taps_timeseries("t-1", days=0, now=now)
    assert len(points) == 1
    assert points[0].date == "2026-05-15"
