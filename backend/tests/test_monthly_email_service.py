"""Tests for the monthly report cron orchestrator (S4-W3).

Same shape as test_reactivation_service: stub the surrounding services,
verify the loop runs to completion under partial failure, and capture
counter accuracy.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import monthly_email_service as svc
from app.services.monthly_report_service import MonthlyReport, PeriodStats


def _report(tenant_id: str = "t-1") -> MonthlyReport:
    return MonthlyReport(
        tenant={"id": tenant_id, "name": "ACME", "slug": "acme"},
        year=2026,
        month=4,
        period_start=datetime(2026, 3, 31, 23, 0, tzinfo=UTC),
        period_end=datetime(2026, 4, 30, 23, 0, tzinfo=UTC),
        current=PeriodStats(),
        previous=PeriodStats(),
        campaigns=[],
    )


@pytest.fixture
def fake_tenants(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    monkeypatch.setattr(svc.tenants, "list_active_for_cron", lambda *_a, **_k: rows)
    return rows


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []

    def fake_send(**kwargs: Any) -> None:
        log.append(kwargs)

    monkeypatch.setattr(svc.email_service, "send_monthly_report", fake_send)
    return log


@pytest.fixture
def computed(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub compute so it returns one of the test reports we control. The
    `failures` dict tells the stub which tenant ids should raise."""
    state: dict[str, Any] = {"failures": {}}

    def fake_compute(*, tenant_id: str, year: int, month: int) -> MonthlyReport:
        exc = state["failures"].get(tenant_id)
        if exc is not None:
            raise exc
        return _report(tenant_id)

    monkeypatch.setattr(svc.monthly_report_service, "compute", fake_compute)
    monkeypatch.setattr(
        svc.pdf_renderer, "render_monthly_report", lambda _r: b"%PDF-1.4\n%fake\n"
    )
    monkeypatch.setattr(svc.pdf_renderer, "report_filename", lambda _r: "smarttap-x.pdf")
    return state


def test_run_monthly_sends_one_email_per_active_tenant(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    fake_tenants.extend([{"id": "t-1"}, {"id": "t-2"}, {"id": "t-3"}])

    result = svc.run_monthly(now=datetime(2026, 5, 1, 6, 30, tzinfo=UTC))

    assert result.year == 2026
    assert result.month == 4
    assert result.tenants_scanned == 3
    assert result.total_sent == 3
    assert [e["tenant_id"] for e in sent_emails] == ["t-1", "t-2", "t-3"]
    # Attached PDF + filename should propagate to the email layer.
    assert sent_emails[0]["pdf_bytes"].startswith(b"%PDF-")
    assert sent_emails[0]["pdf_filename"].endswith(".pdf")


def test_run_monthly_back_fill_with_explicit_year_month(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    fake_tenants.append({"id": "t-1"})

    result = svc.run_monthly(year=2026, month=2)

    assert result.year == 2026
    assert result.month == 2
    assert sent_emails[0]["year"] == 2026
    assert sent_emails[0]["month"] == 2


def test_run_monthly_requires_year_and_month_together(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    with pytest.raises(ValueError):
        svc.run_monthly(year=2026)
    with pytest.raises(ValueError):
        svc.run_monthly(month=5)


def test_run_monthly_skips_tenant_that_disappeared(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    fake_tenants.extend([{"id": "t-good"}, {"id": "t-gone"}])
    computed["failures"]["t-gone"] = NotFoundError("Tenant not found")

    result = svc.run_monthly(year=2026, month=4)

    assert result.tenants_scanned == 2
    assert result.total_sent == 1
    by_id = {r.tenant_id: r for r in result.by_tenant}
    assert by_id["t-gone"].sent is False
    assert by_id["t-gone"].error and "disappeared" in by_id["t-gone"].error


def test_run_monthly_one_compute_failure_doesnt_break_loop(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    fake_tenants.extend([{"id": "t-good"}, {"id": "t-bad"}, {"id": "t-also-good"}])
    computed["failures"]["t-bad"] = RuntimeError("db blew up")

    result = svc.run_monthly(year=2026, month=4)

    assert result.total_sent == 2
    by_id = {r.tenant_id: r for r in result.by_tenant}
    assert by_id["t-bad"].sent is False
    assert by_id["t-bad"].error and "compute" in by_id["t-bad"].error
    # Two emails actually went out, for the surviving tenants.
    assert {e["tenant_id"] for e in sent_emails} == {"t-good", "t-also-good"}


def test_run_monthly_send_failure_records_but_continues(
    fake_tenants: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    computed: dict[str, Any],
) -> None:
    """email_service.send_monthly_report is meant to swallow its own errors,
    but the orchestrator should still cope if a future regression breaks
    that contract — capture the error, keep going."""
    fake_tenants.extend([{"id": "t-1"}, {"id": "t-2"}])
    calls: list[str] = []

    def flaky_send(**kw: Any) -> None:
        calls.append(kw["tenant_id"])
        if kw["tenant_id"] == "t-1":
            raise RuntimeError("resend exploded")

    monkeypatch.setattr(svc.email_service, "send_monthly_report", flaky_send)

    result = svc.run_monthly(year=2026, month=4)

    assert calls == ["t-1", "t-2"]
    assert result.total_sent == 1
    by_id = {r.tenant_id: r for r in result.by_tenant}
    assert by_id["t-1"].error and "send" in by_id["t-1"].error
    assert by_id["t-2"].sent is True


def test_run_monthly_with_no_active_tenants_returns_zero(
    fake_tenants: list[dict[str, Any]],
    sent_emails: list[dict[str, Any]],
    computed: dict[str, Any],
) -> None:
    result = svc.run_monthly(year=2026, month=4)

    assert result.tenants_scanned == 0
    assert result.total_sent == 0
    assert result.by_tenant == []
    assert sent_emails == []
