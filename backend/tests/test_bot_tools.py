"""Tests for the read-only WhatsApp bot tools (S5 Feature 1, Phase A).

These guard the contract Claude depends on: each tool runs scoped to the
injected tenant_id, returns JSON, clamps limits, and maps semantic filters to
the right db filter/sort. DB + dashboard layers are stubbed.
"""

import json
from datetime import datetime
from typing import Any

import pytest

from app.services import bot_tools
from app.services.dashboard_service import OverviewMetrics

TENANT = "t-1"


def test_get_overview_returns_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_overview(tenant_id: str) -> OverviewMetrics:
        captured["tenant_id"] = tenant_id
        return OverviewMetrics(
            customers_total=42,
            taps_week=10,
            reviews_month=3,
            customers_at_risk=5,
            active_stamps_total=88,
            loyalty_visits_today=6,
        )

    monkeypatch.setattr(bot_tools.dashboard_service, "overview", fake_overview)

    out = json.loads(bot_tools.execute("get_overview", TENANT, {}))

    assert captured["tenant_id"] == TENANT  # tenant scope injected, not chosen
    assert out["customers_total"] == 42
    assert out["taps_last_7_days"] == 10
    assert out["reviews_last_30_days"] == 3
    assert out["customers_at_risk_30d"] == 5
    assert out["active_stamps_total"] == 88
    assert out["loyalty_visits_today"] == 6


def test_query_customers_maps_filter_and_clamps_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    monkeypatch.setattr(
        bot_tools.tenants, "get_by_id", lambda tid: {"stamps_for_reward": 10}
    )

    def fake_list(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        calls.update(kwargs)
        return [
            {"name": "Alex", "total_visits": 12, "current_stamps": 4, "last_visit_at": "x"}
        ], 1

    monkeypatch.setattr(bot_tools.customers, "list_for_tenant", fake_list)

    # 'loyal' maps to (all, visits); limit 50 must clamp to 20.
    out = json.loads(
        bot_tools.execute("query_customers", TENANT, {"filter": "loyal", "limit": 50})
    )

    assert calls["tenant_id"] == TENANT
    assert calls["filter_mode"] == "all"
    assert calls["sort"] == "visits"
    assert calls["limit"] == bot_tools.MAX_CUSTOMER_LIMIT  # clamped
    assert out["filter"] == "loyal"
    assert out["total_matching"] == 1
    assert out["showing"][0]["name"] == "Alex"


@pytest.mark.parametrize(
    "semantic,expected",
    [
        ("loyal", ("all", "visits")),
        ("at_risk", ("at_risk", "recent")),
        ("has_reward", ("has_reward", "stamps")),
        ("new", ("all", "recent")),
        ("all", ("all", "recent")),
    ],
)
def test_query_customers_filter_map(
    monkeypatch: pytest.MonkeyPatch,
    semantic: str,
    expected: tuple[str, str],
) -> None:
    calls: dict[str, Any] = {}
    monkeypatch.setattr(bot_tools.tenants, "get_by_id", lambda tid: {"stamps_for_reward": 5})
    monkeypatch.setattr(
        bot_tools.customers,
        "list_for_tenant",
        lambda **kw: (calls.update(kw) or ([], 0)),
    )

    bot_tools.execute("query_customers", TENANT, {"filter": semantic})

    assert (calls["filter_mode"], calls["sort"]) == expected


def test_get_peak_times_finds_busiest(monkeypatch: pytest.MonkeyPatch) -> None:
    # Three taps on a Monday 14:00 UTC, one on Tuesday — Monday/14h wins.
    # 2026-05-25 is a Monday. Dublin in May is UTC+1, so 14:00 UTC = 15:00 local.
    rows = [
        {"created_at": "2026-05-25T14:00:00+00:00"},
        {"created_at": "2026-05-25T14:20:00+00:00"},
        {"created_at": "2026-05-25T14:40:00+00:00"},
        {"created_at": "2026-05-26T09:00:00+00:00"},
    ]
    monkeypatch.setattr(bot_tools.taps, "list_in_range", lambda *a, **k: rows)

    out = json.loads(bot_tools.execute("get_peak_times", TENANT, {"days": 30}))

    assert out["total_taps"] == 4
    assert out["busiest_weekday"]["day"] == "Monday"
    # 14:00 UTC -> 15:00 Europe/Dublin (IST, UTC+1) in May.
    assert out["peak_hour_local_dublin"]["hour_24h"] == 15


def test_get_peak_times_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bot_tools.taps, "list_in_range", lambda *a, **k: [])
    out = json.loads(bot_tools.execute("get_peak_times", TENANT, {"days": 7}))
    assert out["total_taps"] == 0
    assert "note" in out


def test_get_review_performance_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_count(
        tenant_id: str, *, start: datetime, end: datetime, action_taken: str | None = None
    ) -> int:
        return 4 if action_taken == "review_clicked" else 20

    monkeypatch.setattr(bot_tools.taps, "count_in_range", fake_count)

    out = json.loads(bot_tools.execute("get_review_performance", TENANT, {"days": 30}))

    assert out["total_taps"] == 20
    assert out["review_clicks"] == 4
    assert out["tap_to_review_conversion"] == 0.2


def test_review_performance_zero_taps_no_div_by_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bot_tools.taps, "count_in_range", lambda *a, **k: 0)
    out = json.loads(bot_tools.execute("get_review_performance", TENANT, {"days": 7}))
    assert out["tap_to_review_conversion"] == 0.0


def test_days_clamped_to_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_list(tenant_id: str, *, start: datetime, end: datetime, **k: Any) -> list[Any]:
        seen["span_days"] = (end - start).days
        return []

    monkeypatch.setattr(bot_tools.taps, "list_in_range", fake_list)
    bot_tools.execute("get_peak_times", TENANT, {"days": 999})  # not allowed -> 30
    assert seen["span_days"] == 30


def test_unknown_tool_returns_error() -> None:
    out = json.loads(bot_tools.execute("drop_tables", TENANT, {}))
    assert "error" in out
