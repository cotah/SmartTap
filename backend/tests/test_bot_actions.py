"""Tests for the WhatsApp bot write actions (S5 Feature 1, Phase B).

handle_write_tool (prepare/confirm/direct + trial gate) and execute_action
(maps tool -> service). All services stubbed.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.services import bot_actions as ba

NOW = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
TENANT = "t-1"
PHONE = "353871234567"


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "trial": "active",
        "inactive_count": 3,
        "pending": [],
        "reactivation_sent": 5,
        "campaign_raises": None,
        "report_sent": "msg-1",
    }

    monkeypatch.setattr(ba.trial_service, "compute_trial_status", lambda t, **k: state["trial"])
    monkeypatch.setattr(
        ba.customers,
        "find_inactive_for_reactivation",
        lambda **kw: [{} for _ in range(state["inactive_count"])],
    )
    monkeypatch.setattr(
        ba.whatsapp,
        "set_pending_action",
        lambda phone, action, expires: state["pending"].append(action),
    )
    monkeypatch.setattr(
        ba.reactivation_service,
        "run_for_tenant",
        lambda tid, **k: SimpleNamespace(sent=state["reactivation_sent"]),
    )

    def fake_create(**kw: Any) -> dict[str, Any]:
        if state["campaign_raises"]:
            raise state["campaign_raises"]
        return {"id": "camp-1", **kw}

    monkeypatch.setattr(ba.campaign_service, "create_double_stamp", fake_create)

    monkeypatch.setattr(
        ba.monthly_report_service, "resolve_previous_complete_month", lambda now: (2026, 4)
    )
    monkeypatch.setattr(ba.monthly_report_service, "compute", lambda **kw: SimpleNamespace())
    monkeypatch.setattr(ba.pdf_renderer, "render_monthly_report", lambda r: b"PDF")
    monkeypatch.setattr(ba.pdf_renderer, "report_filename", lambda r: "report.pdf")
    monkeypatch.setattr(ba.whatsapp_client, "send_document", lambda **kw: state["report_sent"])
    return state


# ---------------------------------------------------------------------------
# handle_write_tool — confirmable
# ---------------------------------------------------------------------------


def test_reactivation_registers_pending_with_count(stubs: dict[str, Any]) -> None:
    out = ba.handle_write_tool(
        name="send_reactivation",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={},
        now=NOW,
    )
    assert "CONFIRMATION NEEDED" in out
    assert "3 customer" in out
    assert stubs["pending"] == [{"tool": "send_reactivation"}]


def test_trial_expired_blocks_action(stubs: dict[str, Any]) -> None:
    stubs["trial"] = "expired"
    out = ba.handle_write_tool(
        name="send_reactivation",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={},
        now=NOW,
    )
    assert "active subscription" in out
    assert stubs["pending"] == []  # nothing registered


def test_double_stamp_registers_parsed_window(stubs: dict[str, Any]) -> None:
    out = ba.handle_write_tool(
        name="create_double_stamp",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={
            "name": "Weekend",
            "starts_at": "2026-05-30T00:00:00+00:00",
            "ends_at": "2026-05-31T23:59:00+00:00",
            "multiplier": 2,
        },
        now=NOW,
    )
    assert "CONFIRMATION NEEDED" in out
    assert "2026-05-30" in out and "2026-05-31" in out
    action = stubs["pending"][0]
    assert action["tool"] == "create_double_stamp"
    assert action["name"] == "Weekend"
    assert action["multiplier"] == 2


def test_double_stamp_bad_dates(stubs: dict[str, Any]) -> None:
    out = ba.handle_write_tool(
        name="create_double_stamp",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={"starts_at": "not-a-date", "ends_at": "also-bad"},
        now=NOW,
    )
    assert "couldn't understand" in out.lower()
    assert stubs["pending"] == []


# ---------------------------------------------------------------------------
# handle_write_tool — direct (monthly report)
# ---------------------------------------------------------------------------


def test_monthly_report_sends_directly(stubs: dict[str, Any]) -> None:
    out = ba.handle_write_tool(
        name="send_monthly_report",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={},
        now=NOW,
    )
    assert "sent" in out.lower()
    assert stubs["pending"] == []  # no confirmation for owner-facing report


def test_monthly_report_noop_when_whatsapp_unavailable(stubs: dict[str, Any]) -> None:
    stubs["report_sent"] = None  # send_document no-op
    out = ba.handle_write_tool(
        name="send_monthly_report",
        tenant_id=TENANT,
        phone=PHONE,
        tenant={"id": TENANT},
        tool_input={},
        now=NOW,
    )
    assert "isn't available" in out or "dashboard" in out


# ---------------------------------------------------------------------------
# execute_action
# ---------------------------------------------------------------------------


def test_execute_reactivation(stubs: dict[str, Any]) -> None:
    out = ba.execute_action(TENANT, {"tool": "send_reactivation"}, now=NOW)
    assert "5 customer" in out


def test_execute_double_stamp_success(stubs: dict[str, Any]) -> None:
    out = ba.execute_action(
        TENANT,
        {
            "tool": "create_double_stamp",
            "name": "Weekend",
            "starts_at": "2026-05-30T00:00:00+00:00",
            "ends_at": "2026-05-31T23:59:00+00:00",
            "multiplier": 2,
        },
        now=NOW,
    )
    assert "active" in out.lower()


def test_execute_double_stamp_conflict(stubs: dict[str, Any]) -> None:
    from app.services.campaign_service import ConflictingCampaignError

    stubs["campaign_raises"] = ConflictingCampaignError("already active")
    out = ba.execute_action(
        TENANT,
        {
            "tool": "create_double_stamp",
            "starts_at": "2026-05-30T00:00:00+00:00",
            "ends_at": "2026-05-31T23:59:00+00:00",
        },
        now=NOW,
    )
    assert "already have an active" in out.lower()
