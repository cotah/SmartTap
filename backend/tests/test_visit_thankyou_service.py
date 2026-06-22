"""Tests for the real-time post-visit thank-you policy (visit_thankyou_service).

This service is a single-customer decision, not a cron, so the tests are a
straight policy matrix: each rule (kill-switch, stamp, consent, email, token,
cooldown) gets a case, plus the happy path's mark-before-send + URL wiring and
the error containment that keeps a BackgroundTask from ever blowing up the tap.

The DB mark and the email send are stubbed — same contract the reactivation and
review_nudge tests use.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.services import visit_thankyou_service as svc

NOW = datetime(2026, 6, 22, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Stubs + fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def marks(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, datetime]]:
    log: list[tuple[str, datetime]] = []
    monkeypatch.setattr(svc.customers, "mark_thankyou_sent", lambda cid, at: log.append((cid, at)))
    return log


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []

    def fake_send(**kwargs: Any) -> bool:
        log.append(kwargs)
        return True

    monkeypatch.setattr(svc.email_service, "send_visit_thankyou", fake_send)
    return log


@pytest.fixture(autouse=True)
def settings(monkeypatch: pytest.MonkeyPatch) -> "FakeSettings":
    fake = FakeSettings()
    monkeypatch.setattr(svc, "get_settings", lambda: fake)
    return fake


class FakeSettings:
    def __init__(self) -> None:
        self.thankyou_enabled = True
        self.site_url = "https://smarttap.test"


def _tenant(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "t-1",
        "name": "ACME Barber",
        "stamps_for_reward": 10,
        "reward_description": "a free cut",
        "google_review_url": "https://g.page/r/acme",
    }
    base.update(over)
    return base


def _customer(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "c-1",
        "name": "Alex",
        "email": "alex@example.test",
        "current_stamps": 4,
        "gdpr_consent": True,
        "magic_link_token": "tok_abc",
        "last_thankyou_sent_at": None,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_sends_and_marks_cooldown(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    res = svc.maybe_send(tenant=_tenant(), customer=_customer(), stamp_awarded=True, now=NOW)

    assert res.status == "sent"
    assert marks == [("c-1", NOW)]
    assert len(sent) == 1


def test_builds_review_and_opt_out_and_magic_urls(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    svc.maybe_send(
        tenant=_tenant(google_review_url="https://g.page/r/acme"),
        customer=_customer(magic_link_token="tokA"),
        stamp_awarded=True,
        now=NOW,
    )

    call = sent[0]
    assert call["review_url"] == "https://g.page/r/acme"
    assert call["opt_out_url"] == "https://smarttap.test/u/tokA"
    assert call["magic_link_url"] == "https://smarttap.test/m/tokA"


def test_review_url_is_none_when_tenant_has_none(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    """Loyalty-only tenant: review_url passed through as None so the template
    falls back to the stamp-card CTA. Still sent (the stamp progress is value)."""
    svc.maybe_send(
        tenant=_tenant(google_review_url=None),
        customer=_customer(),
        stamp_awarded=True,
        now=NOW,
    )
    assert sent[0]["review_url"] is None


def test_blank_review_url_normalised_to_none(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    svc.maybe_send(
        tenant=_tenant(google_review_url="   "),
        customer=_customer(),
        stamp_awarded=True,
        now=NOW,
    )
    assert sent[0]["review_url"] is None


# ---------------------------------------------------------------------------
# Policy gates — each returns a distinct skip status and sends nothing
# ---------------------------------------------------------------------------


def test_skips_when_kill_switch_off(
    settings: FakeSettings, marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    settings.thankyou_enabled = False
    res = svc.maybe_send(tenant=_tenant(), customer=_customer(), stamp_awarded=True, now=NOW)

    assert res.status == "skipped_disabled"
    assert marks == []
    assert sent == []


def test_skips_when_no_stamp_awarded(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    res = svc.maybe_send(tenant=_tenant(), customer=_customer(), stamp_awarded=False, now=NOW)

    assert res.status == "skipped_no_stamp"
    assert sent == []


def test_skips_without_gdpr_consent(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    res = svc.maybe_send(
        tenant=_tenant(), customer=_customer(gdpr_consent=False), stamp_awarded=True, now=NOW
    )

    assert res.status == "skipped_no_consent"
    assert marks == []
    assert sent == []


def test_skips_without_email(marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]) -> None:
    res = svc.maybe_send(
        tenant=_tenant(), customer=_customer(email=None), stamp_awarded=True, now=NOW
    )

    assert res.status == "skipped_no_email"
    assert sent == []


def test_skips_without_magic_token(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    res = svc.maybe_send(
        tenant=_tenant(), customer=_customer(magic_link_token=None), stamp_awarded=True, now=NOW
    )

    assert res.status == "skipped_no_token"
    assert sent == []


# ---------------------------------------------------------------------------
# Cooldown — the 6h dedupe window
# ---------------------------------------------------------------------------


def test_skips_within_cooldown_window(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    # Thanked 2h ago → still inside the 6h window.
    recent = (NOW - timedelta(hours=2)).isoformat()
    res = svc.maybe_send(
        tenant=_tenant(),
        customer=_customer(last_thankyou_sent_at=recent),
        stamp_awarded=True,
        now=NOW,
    )

    assert res.status == "skipped_cooldown"
    assert marks == []
    assert sent == []


def test_sends_again_after_cooldown_expires(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    # Thanked 7h ago → cooldown expired, a genuine new visit gets a thank-you.
    old = (NOW - timedelta(hours=7)).isoformat()
    res = svc.maybe_send(
        tenant=_tenant(),
        customer=_customer(last_thankyou_sent_at=old),
        stamp_awarded=True,
        now=NOW,
    )

    assert res.status == "sent"
    assert marks == [("c-1", NOW)]
    assert len(sent) == 1


def test_unparseable_last_sent_does_not_block(
    marks: list[tuple[str, datetime]], sent: list[dict[str, Any]]
) -> None:
    res = svc.maybe_send(
        tenant=_tenant(),
        customer=_customer(last_thankyou_sent_at="garbage"),
        stamp_awarded=True,
        now=NOW,
    )
    assert res.status == "sent"


# ---------------------------------------------------------------------------
# Error containment — a BackgroundTask must never raise into nothing useful
# ---------------------------------------------------------------------------


def test_send_exception_is_contained_and_marked(
    marks: list[tuple[str, datetime]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(**_kw: Any) -> bool:
        raise RuntimeError("Resend down")

    monkeypatch.setattr(svc.email_service, "send_visit_thankyou", boom)

    res = svc.maybe_send(tenant=_tenant(), customer=_customer(), stamp_awarded=True, now=NOW)

    # Contained, not raised. Marked before the failure (mark-before-send), so a
    # retried tap won't double-send.
    assert res.status == "error"
    assert marks == [("c-1", NOW)]
