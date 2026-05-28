"""Tests for the review-nudge cron orchestrator (S5 Feature 2).

Two layers are exercised:

    1. `_candidate_customer_ids` — the pure detection rule (who tapped, earned
       a stamp in the window, and never clicked review since). This is where
       the off-by-one risk lives, so it's tested directly.
    2. `run_daily` — the orchestration: GDPR/email/cooldown filtering happens
       in the DB layer (stubbed here), mark-before-send, per-customer error
       isolation, and the tenant-level google_review_url gate.

DB and email layers are stubbed — the same contract reactivation's tests use.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.services import review_nudge_service as svc

# ---------------------------------------------------------------------------
# Fixed clock + helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)


def _iso(dt: datetime) -> str:
    """Render like Supabase does (explicit offset)."""
    return dt.isoformat()


def _signal(customer_id: str, action: str, *, hours_ago: float) -> dict[str, Any]:
    return {
        "customer_id": customer_id,
        "action_taken": action,
        "created_at": _iso(NOW - timedelta(hours=hours_ago)),
    }


# The window run_daily computes from NOW, reused by the unit tests.
LOOKBACK_SINCE = NOW - timedelta(days=svc.LOOKBACK_DAYS)
NUDGE_BEFORE = NOW - timedelta(hours=svc.NUDGE_AFTER_HOURS)


# ---------------------------------------------------------------------------
# Unit: _candidate_customer_ids (the detection rule)
# ---------------------------------------------------------------------------


def _candidates(signals: list[dict[str, Any]]) -> list[str]:
    return svc._candidate_customer_ids(
        signals, lookback_since=LOOKBACK_SINCE, nudge_before=NUDGE_BEFORE
    )


def test_stamp_in_window_no_review_is_candidate() -> None:
    # 48h ago: older than 24h, newer than 7d → in window.
    assert _candidates([_signal("c-1", "stamp_earned", hours_ago=48)]) == ["c-1"]


def test_stamp_too_recent_is_not_candidate() -> None:
    # 2h ago: they basically just visited — don't pester.
    assert _candidates([_signal("c-1", "stamp_earned", hours_ago=2)]) == []


def test_stamp_older_than_lookback_is_not_candidate() -> None:
    # 8 days ago: outside the 7-day lookback. (In prod the query wouldn't even
    # return it; the guard defends against a widened query.)
    assert _candidates([_signal("c-1", "stamp_earned", hours_ago=8 * 24)]) == []


def test_review_clicked_after_stamp_is_not_candidate() -> None:
    signals = [
        _signal("c-1", "stamp_earned", hours_ago=48),
        _signal("c-1", "review_clicked", hours_ago=47),  # after the stamp
    ]
    assert _candidates(signals) == []


def test_review_clicked_before_stamp_still_candidate() -> None:
    # An old review then a fresh un-reviewed visit → nudge for the new visit.
    signals = [
        _signal("c-1", "review_clicked", hours_ago=72),
        _signal("c-1", "stamp_earned", hours_ago=48),
    ]
    assert _candidates(signals) == ["c-1"]


def test_most_recent_stamp_wins() -> None:
    # Old stamp in window + a brand-new stamp (2h ago) → most recent is too
    # recent → not a candidate (they just came back).
    signals = [
        _signal("c-1", "stamp_earned", hours_ago=48),
        _signal("c-1", "stamp_earned", hours_ago=2),
    ]
    assert _candidates(signals) == []


def test_unparseable_or_missing_rows_are_skipped() -> None:
    signals = [
        {"customer_id": None, "action_taken": "stamp_earned", "created_at": _iso(NOW)},
        {"customer_id": "c-1", "action_taken": "stamp_earned", "created_at": "garbage"},
        _signal("c-2", "stamp_earned", hours_ago=48),
    ]
    assert _candidates(signals) == ["c-2"]


# ---------------------------------------------------------------------------
# Integration scaffolding (stubbed DB + email)
# ---------------------------------------------------------------------------


class FakeTapsDB:
    def __init__(self) -> None:
        self.signals_by_tenant: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[tuple[str, datetime]] = []

    def list_customer_review_signals(
        self, tenant_id: str, *, since: datetime, limit: int = 10_000
    ) -> list[dict[str, Any]]:
        self.calls.append((tenant_id, since))
        return self.signals_by_tenant.get(tenant_id, [])


class FakeCustomersDB:
    """Models the SQL gdpr/email/cooldown filter: only customers placed in
    `eligible_rows` are returned, and only when their id is in the candidate
    set the service passes in."""

    def __init__(self) -> None:
        # tenant_id -> {customer_id: row}
        self.eligible_rows: dict[str, dict[str, dict[str, Any]]] = {}
        self.marks: list[tuple[str, datetime]] = []
        self.find_calls: list[dict[str, Any]] = []

    def find_review_nudge_eligible(
        self,
        *,
        tenant_id: str,
        customer_ids: list[str],
        cooldown_cutoff: datetime,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        self.find_calls.append(
            {
                "tenant_id": tenant_id,
                "customer_ids": list(customer_ids),
                "cooldown_cutoff": cooldown_cutoff,
                "limit": limit,
            }
        )
        store = self.eligible_rows.get(tenant_id, {})
        return [store[cid] for cid in customer_ids if cid in store][:limit]

    def mark_review_nudge_sent(self, customer_id: str, sent_at: datetime) -> None:
        self.marks.append((customer_id, sent_at))


class FakeTenantsDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def list_active_for_cron(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        return self.rows[:limit]


@pytest.fixture
def fake_taps(monkeypatch: pytest.MonkeyPatch) -> FakeTapsDB:
    fake = FakeTapsDB()
    monkeypatch.setattr(
        svc.taps, "list_customer_review_signals", fake.list_customer_review_signals
    )
    return fake


@pytest.fixture
def fake_customers(monkeypatch: pytest.MonkeyPatch) -> FakeCustomersDB:
    fake = FakeCustomersDB()
    monkeypatch.setattr(
        svc.customers, "find_review_nudge_eligible", fake.find_review_nudge_eligible
    )
    monkeypatch.setattr(
        svc.customers, "mark_review_nudge_sent", fake.mark_review_nudge_sent
    )
    return fake


@pytest.fixture
def fake_tenants(monkeypatch: pytest.MonkeyPatch) -> FakeTenantsDB:
    fake = FakeTenantsDB(rows=[])
    monkeypatch.setattr(svc.tenants, "list_active_for_cron", fake.list_active_for_cron)
    return fake


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []

    def fake_send(**kwargs: Any) -> bool:
        log.append(kwargs)
        return True

    monkeypatch.setattr(svc.email_service, "send_review_nudge", fake_send)
    return log


@pytest.fixture(autouse=True)
def fixed_site_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import config

    class FakeSettings:
        site_url = "https://smarttap.test"

    monkeypatch.setattr(config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(svc, "get_settings", lambda: FakeSettings())


def _tenant(tid: str, *, review_url: str | None = "https://g.page/r/acme") -> dict[str, Any]:
    return {
        "id": tid,
        "name": "ACME Barber",
        "stamps_for_reward": 10,
        "reward_description": "free cut",
        "google_review_url": review_url,
    }


def _eligible_row(cid: str, *, token: str | None = "tok") -> dict[str, Any]:
    return {"id": cid, "name": "Alex", "email": f"{cid}@x.test", "magic_link_token": token}


# ---------------------------------------------------------------------------
# Integration: run_daily
# ---------------------------------------------------------------------------


def test_run_daily_sends_and_marks_cooldown(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [_tenant("t-1")]
    fake_taps.signals_by_tenant["t-1"] = [_signal("c-1", "stamp_earned", hours_ago=48)]
    fake_customers.eligible_rows["t-1"] = {"c-1": _eligible_row("c-1")}

    result = svc.run_daily(now=NOW)

    assert result.tenants_scanned == 1
    assert result.total_sent == 1
    assert len(sent) == 1
    assert fake_customers.marks == [("c-1", NOW)]
    # The candidate set and the 30-day cooldown cutoff were wired correctly.
    assert fake_customers.find_calls[0]["customer_ids"] == ["c-1"]
    assert fake_customers.find_calls[0]["cooldown_cutoff"] == NOW - timedelta(days=30)


def test_run_daily_builds_review_and_opt_out_urls(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [_tenant("t-1", review_url="https://g.page/r/acme")]
    fake_taps.signals_by_tenant["t-1"] = [_signal("c-1", "stamp_earned", hours_ago=48)]
    fake_customers.eligible_rows["t-1"] = {"c-1": _eligible_row("c-1", token="tokA")}

    svc.run_daily(now=NOW)

    assert sent[0]["review_url"] == "https://g.page/r/acme"
    assert sent[0]["opt_out_url"] == "https://smarttap.test/u/tokA"


def test_run_daily_skips_tenant_without_review_url(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [_tenant("t-1", review_url=None)]
    # Even if there were eligible customers, the tenant gate fires first.
    fake_taps.signals_by_tenant["t-1"] = [_signal("c-1", "stamp_earned", hours_ago=48)]
    fake_customers.eligible_rows["t-1"] = {"c-1": _eligible_row("c-1")}

    result = svc.run_daily(now=NOW)

    assert result.total_sent == 0
    assert sent == []
    # We short-circuit before even querying taps for that tenant.
    assert fake_taps.calls == []


def test_run_daily_skips_customer_without_magic_token(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [_tenant("t-1")]
    fake_taps.signals_by_tenant["t-1"] = [
        _signal("c-1", "stamp_earned", hours_ago=48),
        _signal("c-2", "stamp_earned", hours_ago=48),
    ]
    fake_customers.eligible_rows["t-1"] = {
        "c-1": _eligible_row("c-1", token=None),
        "c-2": _eligible_row("c-2", token="tokB"),
    }

    result = svc.run_daily(now=NOW)

    assert result.total_sent == 1
    assert sent[0]["customer"]["id"] == "c-2"
    # Broken row not marked → it retries once the token is repaired.
    assert {cid for cid, _ in fake_customers.marks} == {"c-2"}
    assert any("c-1" in e for e in result.by_tenant[0].errors)


def test_run_daily_per_customer_send_exception_is_isolated(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_tenants.rows = [_tenant("t-1")]
    fake_taps.signals_by_tenant["t-1"] = [
        _signal("c-1", "stamp_earned", hours_ago=48),
        _signal("c-2", "stamp_earned", hours_ago=48),
    ]
    fake_customers.eligible_rows["t-1"] = {
        "c-1": _eligible_row("c-1", token="tokA"),
        "c-2": _eligible_row("c-2", token="tokB"),
    }

    calls: list[str] = []

    def flaky(**kw: Any) -> bool:
        cid = kw["customer"]["id"]
        calls.append(cid)
        if cid == "c-1":
            raise RuntimeError("Resend hiccup")
        return True

    monkeypatch.setattr(svc.email_service, "send_review_nudge", flaky)

    result = svc.run_daily(now=NOW)

    assert calls == ["c-1", "c-2"]
    assert result.total_sent == 1  # only c-2 returned cleanly
    # Both marked (mark-before-send) — lose a cycle rather than double-send.
    assert {cid for cid, _ in fake_customers.marks} == {"c-1", "c-2"}
    assert any("c-1" in e for e in result.by_tenant[0].errors)


def test_run_daily_customer_who_reviewed_is_not_sent(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [_tenant("t-1")]
    fake_taps.signals_by_tenant["t-1"] = [
        _signal("c-1", "stamp_earned", hours_ago=48),
        _signal("c-1", "review_clicked", hours_ago=47),
    ]
    fake_customers.eligible_rows["t-1"] = {"c-1": _eligible_row("c-1")}

    result = svc.run_daily(now=NOW)

    assert result.total_sent == 0
    assert sent == []
    # c-1 never became a candidate, so it wasn't even offered to the DB filter.
    assert fake_customers.find_calls[0]["customer_ids"] == []


def test_run_daily_no_active_tenants_returns_zero(
    fake_tenants: FakeTenantsDB,
    fake_taps: FakeTapsDB,
    fake_customers: FakeCustomersDB,
    sent: list[dict[str, Any]],
) -> None:
    result = svc.run_daily(now=NOW)

    assert result.tenants_scanned == 0
    assert result.total_sent == 0
    assert result.by_tenant == []
    assert sent == []
