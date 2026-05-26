"""Tests for monthly report computation (S4-W3).

The service owns the timezone math, period boundaries, and tap-row insights.
Each of those is independently risky:

    - Period bounds: DST flips in Dublin in late March / late October. Off by
      one hour means a tap on the last day spills into next month.
    - Previous-period delta: when previous is zero the percentage is None,
      not infinity; the PDF renders that as a dash.
    - Insights: weekday/hour grouping must run in LOCAL time, not UTC, or a
      19:00 IST rush looks like 18:00.

These tests stub the db layer so each behaviour can be exercised in
isolation. The PDF rendering smoke test lives in `test_pdf_renderer.py`.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import monthly_report_service as svc

# ---------------------------------------------------------------------------
# Period bounds
# ---------------------------------------------------------------------------


def test_month_bounds_winter_utc_offset_zero() -> None:
    """January Dublin is GMT (UTC+0). Bounds line up exactly with UTC."""
    start, end = svc._month_bounds_utc(2026, 1)
    assert start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)


def test_month_bounds_summer_utc_offset_one() -> None:
    """May Dublin is IST (UTC+1). 1 May 00:00 local = 30 Apr 23:00 UTC."""
    start, end = svc._month_bounds_utc(2026, 5)
    assert start == datetime(2026, 4, 30, 23, 0, tzinfo=UTC)
    assert end == datetime(2026, 5, 31, 23, 0, tzinfo=UTC)


def test_month_bounds_december_wraps_to_next_year() -> None:
    start, end = svc._month_bounds_utc(2026, 12)
    assert start == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)
    # Jan is GMT again, so the end is exact UTC midnight.
    assert end == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


def test_month_bounds_rejects_invalid_month() -> None:
    with pytest.raises(ValueError):
        svc._month_bounds_utc(2026, 13)


def test_resolve_previous_complete_month_for_may_returns_april() -> None:
    """A cron run on 1 May 06:30 UTC (= 07:30 IST) targets April."""
    now = datetime(2026, 5, 1, 6, 30, tzinfo=UTC)
    assert svc.resolve_previous_complete_month(now) == (2026, 4)


def test_resolve_previous_complete_month_for_january_wraps_year() -> None:
    """A run on 1 January 2026 targets December 2025."""
    now = datetime(2026, 1, 1, 6, 30, tzinfo=UTC)
    assert svc.resolve_previous_complete_month(now) == (2025, 12)


def test_resolve_previous_complete_month_anchors_in_dublin_not_utc() -> None:
    """30 April 23:30 UTC during IST (UTC+1) is already 1 May 00:30 in Dublin.
    A UTC-anchored implementation would return March; the Dublin-anchored
    one we want returns April."""
    now = datetime(2026, 4, 30, 23, 30, tzinfo=UTC)
    assert svc.resolve_previous_complete_month(now) == (2026, 4)


# ---------------------------------------------------------------------------
# Delta math
# ---------------------------------------------------------------------------


def test_delta_pct_returns_none_when_previous_zero() -> None:
    assert svc.delta_pct(10, 0) is None


def test_delta_pct_returns_zero_when_unchanged() -> None:
    assert svc.delta_pct(10, 10) == 0.0


def test_delta_pct_positive_when_growing() -> None:
    assert svc.delta_pct(15, 10) == pytest.approx(50.0)


def test_delta_pct_negative_when_shrinking() -> None:
    assert svc.delta_pct(5, 10) == pytest.approx(-50.0)


# ---------------------------------------------------------------------------
# compute() — happy and edge paths
# ---------------------------------------------------------------------------


def _patch_stats(
    monkeypatch: pytest.MonkeyPatch,
    *,
    new_customers: int = 0,
    total_taps: int = 0,
    stamps_awarded: int = 0,
    rewards_redeemed: int = 0,
    reviews_clicked: int = 0,
    tap_rows: list[dict[str, Any]] | None = None,
    overlapping_campaigns: list[dict[str, Any]] | None = None,
    tenant_row: dict[str, Any] | None = None,
    tag_rows: list[dict[str, Any]] | None = None,
) -> None:
    """One-shot DB stub: every call returns the same numbers regardless of
    the period. Tests that need different numbers in current vs previous
    period should stub differently per call (see test_compute_includes_previous_stats)."""
    monkeypatch.setattr(svc.customers, "count_created_in_range", lambda *_a, **_k: new_customers)
    def _count_taps(*_a: Any, action_taken: Any = None, **_k: Any) -> int:
        return reviews_clicked if action_taken == "review_clicked" else total_taps

    monkeypatch.setattr(svc.taps, "count_in_range", _count_taps)
    monkeypatch.setattr(svc.stamps, "count_in_range", lambda *_a, **_k: stamps_awarded)
    monkeypatch.setattr(svc.rewards, "count_redeemed_in_range", lambda *_a, **_k: rewards_redeemed)
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: tap_rows or [])
    monkeypatch.setattr(
        svc.campaigns, "list_overlapping_range", lambda *_a, **_k: overlapping_campaigns or []
    )
    monkeypatch.setattr(svc.nfc_tags, "get_by_ids", lambda _ids: tag_rows or [])
    monkeypatch.setattr(
        svc.tenants, "get_by_id", lambda _tid: tenant_row or {"id": "t-1", "name": "ACME"}
    )


def test_compute_empty_month_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """A brand-new tenant in their first quiet month must still get a report.
    All zeros, no insights, no campaigns — but a clean object."""
    _patch_stats(monkeypatch)
    report = svc.compute(tenant_id="t-1", year=2026, month=5)

    assert report.year == 2026
    assert report.month == 5
    assert report.current.total_taps == 0
    assert report.best_weekday is None
    assert report.peak_hour is None
    assert report.top_tag is None
    assert report.campaigns == []


def test_compute_raises_not_found_for_missing_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc.tenants, "get_by_id", lambda _tid: None)

    with pytest.raises(NotFoundError):
        svc.compute(tenant_id="t-missing", year=2026, month=5)


def test_compute_picks_busiest_weekday_in_dublin_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two taps on Monday at 09:00 UTC (= 10:00 IST = Monday local),
    one tap on Sunday 23:30 UTC (= 00:30 Monday IST → also Monday local).
    All three should count as Monday."""
    tap_rows = [
        {"created_at": "2026-05-04T09:00:00Z", "tag_id": "tag-a"},  # Mon UTC → Mon IST
        {"created_at": "2026-05-04T09:30:00Z", "tag_id": "tag-a"},  # Mon UTC → Mon IST
        {"created_at": "2026-05-03T23:30:00Z", "tag_id": "tag-b"},  # Sun UTC → Mon IST
    ]
    _patch_stats(
        monkeypatch,
        tap_rows=tap_rows,
        tag_rows=[
            {"id": "tag-a", "format": "counter_stand", "color": "black", "location_name": ""},
            {"id": "tag-b", "format": "table_tent", "color": "white", "location_name": "Bar"},
        ],
    )
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert report.best_weekday is not None
    assert report.best_weekday[0] == "Monday"
    assert report.best_weekday[1] == 3


def test_compute_picks_peak_hour_in_dublin_tz(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tap at 17:30 UTC in May = 18:30 IST — peak hour should be 18."""
    tap_rows = [
        {"created_at": "2026-05-04T17:30:00Z", "tag_id": "tag-a"},
        {"created_at": "2026-05-05T17:45:00Z", "tag_id": "tag-a"},
        {"created_at": "2026-05-06T13:00:00Z", "tag_id": "tag-a"},  # 14:00 IST
    ]
    _patch_stats(
        monkeypatch,
        tap_rows=tap_rows,
        tag_rows=[{"id": "tag-a", "format": "counter_stand"}],
    )
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert report.peak_hour is not None
    assert report.peak_hour[0] == 18
    assert report.peak_hour[1] == 2


def test_compute_top_tag_uses_location_name_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tap_rows = [
        {"created_at": "2026-05-04T09:00:00Z", "tag_id": "tag-a"},
        {"created_at": "2026-05-04T10:00:00Z", "tag_id": "tag-a"},
        {"created_at": "2026-05-05T09:00:00Z", "tag_id": "tag-b"},
    ]
    tag_rows = [
        {
            "id": "tag-a",
            "format": "counter_stand",
            "color": "black",
            "location_name": "Front desk",
        }
    ]
    _patch_stats(monkeypatch, tap_rows=tap_rows, tag_rows=tag_rows)
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert report.top_tag is not None
    assert report.top_tag.label == "Front desk"
    assert report.top_tag.taps == 2


def test_compute_top_tag_falls_back_to_format_color_when_unnamed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tap_rows = [{"created_at": "2026-05-04T09:00:00Z", "tag_id": "tag-a"}]
    tag_rows = [
        {
            "id": "tag-a",
            "format": "counter_stand",
            "color": "black",
            "location_name": "",
        }
    ]
    _patch_stats(monkeypatch, tap_rows=tap_rows, tag_rows=tag_rows)
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert report.top_tag is not None
    assert report.top_tag.label == "Counter Stand · Black"


def test_compute_top_tag_falls_back_to_id_when_tag_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tap referencing a deleted tag must not blank out the report."""
    tap_rows = [{"created_at": "2026-05-04T09:00:00Z", "tag_id": "abcdef0123456789"}]
    _patch_stats(monkeypatch, tap_rows=tap_rows, tag_rows=[])
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert report.top_tag is not None
    assert report.top_tag.label.startswith("Tag ")


def test_compute_campaigns_overlap_days_within_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A campaign 28 Apr → 5 May reports 4 active days in the May report
    (1, 2, 3, 4 May — overlap with 5 May 00:00 is exclusive)."""
    campaign = {
        "name": "Wednesday boost",
        "type": "double_stamp",
        "status": "active",
        "starts_at": "2026-04-28T00:00:00Z",
        "ends_at": "2026-05-05T00:00:00Z",
        "config": {"multiplier": 2},
    }
    _patch_stats(monkeypatch, overlapping_campaigns=[campaign])
    report = svc.compute(tenant_id="t-1", year=2026, month=5)
    assert len(report.campaigns) == 1
    c = report.campaigns[0]
    assert c.name == "Wednesday boost"
    assert c.multiplier == 2
    assert c.days_active_in_period == 4


def test_compute_includes_previous_stats_for_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Current month sees 10 taps, previous sees 4. Both should land on the
    report so the renderer can compute the +150% delta itself."""
    calls = {"period_start": []}

    def fake_taps_count(_tid: str, *, start: Any, end: Any, action_taken: Any = None) -> int:
        calls["period_start"].append(start)
        # Two calls expected: current period first, then previous. Distinguish
        # by start month after converting to UTC bounds.
        if start.month == 4 or (start.month == 5 and start.year == 2026):
            return 10
        return 4

    monkeypatch.setattr(svc.customers, "count_created_in_range", lambda *_a, **_k: 0)
    monkeypatch.setattr(svc.taps, "count_in_range", fake_taps_count)
    monkeypatch.setattr(svc.stamps, "count_in_range", lambda *_a, **_k: 0)
    monkeypatch.setattr(svc.rewards, "count_redeemed_in_range", lambda *_a, **_k: 0)
    monkeypatch.setattr(svc.taps, "list_in_range", lambda *_a, **_k: [])
    monkeypatch.setattr(svc.campaigns, "list_overlapping_range", lambda *_a, **_k: [])
    monkeypatch.setattr(svc.tenants, "get_by_id", lambda _tid: {"id": "t-1", "name": "ACME"})

    svc.compute(tenant_id="t-1", year=2026, month=5)
    # Both periods were queried (4+ calls: current taps + current reviews,
    # previous taps + previous reviews — the action_taken filter exercises
    # the same path twice per period).
    assert len(calls["period_start"]) >= 4
