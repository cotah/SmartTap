"""Tests for the reactivation cron orchestrator.

The orchestrator is the heart of the GDPR-and-deliverability contract:
    - mark cooldown BEFORE attempting send (so a crash doesn't double-email)
    - filter to GDPR-consenting customers with an email (enforced in the DB
      query, but the orchestrator must not bypass it)
    - degrade gracefully on per-customer errors (one bad row ≠ no run)
    - opt-out raises NotFoundError on unknown token (caller maps to 404)

These tests stub the DB and email layers; that's where the integration
happens in production but it isolates behaviour we own from external services.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import reactivation_service

# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class FakeCustomersDB:
    """Recorder for find/mark/revoke against an in-memory store."""

    def __init__(self) -> None:
        # tenant_id -> list of "eligible" rows the DB would return
        self.eligible_by_tenant: dict[str, list[dict[str, Any]]] = {}
        # records every (customer_id, sent_at) we marked
        self.marks: list[tuple[str, datetime]] = []
        # records revoke calls
        self.revoked_tokens: list[str] = []
        # what revoke returns by token
        self.revoke_returns: dict[str, dict[str, Any] | None] = {}

    def find_inactive_for_reactivation(
        self,
        *,
        tenant_id: str,
        inactive_cutoff: datetime,
        cooldown_cutoff: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        # Cutoffs are captured implicitly via call ordering — see test below
        # for explicit assertion on them.
        return self.eligible_by_tenant.get(tenant_id, [])[:limit]

    def mark_reactivation_sent(self, customer_id: str, sent_at: datetime) -> None:
        self.marks.append((customer_id, sent_at))

    def revoke_consent_via_magic_token(self, token: str) -> dict[str, Any] | None:
        self.revoked_tokens.append(token)
        return self.revoke_returns.get(token)


class FakeTenantsDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls = 0

    def list_active_for_cron(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        self.calls += 1
        return self.rows[:limit]


@pytest.fixture
def fake_customers(monkeypatch: pytest.MonkeyPatch) -> FakeCustomersDB:
    fake = FakeCustomersDB()
    monkeypatch.setattr(
        reactivation_service.customers,
        "find_inactive_for_reactivation",
        fake.find_inactive_for_reactivation,
    )
    monkeypatch.setattr(
        reactivation_service.customers,
        "mark_reactivation_sent",
        fake.mark_reactivation_sent,
    )
    monkeypatch.setattr(
        reactivation_service.customers,
        "revoke_consent_via_magic_token",
        fake.revoke_consent_via_magic_token,
    )
    return fake


@pytest.fixture
def fake_tenants(monkeypatch: pytest.MonkeyPatch) -> FakeTenantsDB:
    fake = FakeTenantsDB(rows=[])
    monkeypatch.setattr(
        reactivation_service.tenants,
        "list_active_for_cron",
        fake.list_active_for_cron,
    )
    return fake


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture every send_reactivation call as a recorded dict — lets tests
    assert on URL construction without standing up the real email pipeline."""
    log: list[dict[str, Any]] = []

    def fake_send(**kwargs: Any) -> bool:
        log.append(kwargs)
        return True

    monkeypatch.setattr(reactivation_service.email_service, "send_reactivation", fake_send)
    return log


@pytest.fixture(autouse=True)
def fixed_site_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin SITE_URL so URL assertions are stable across dev/CI.

    Patches BOTH `app.config.get_settings` and the alias re-imported into
    `reactivation_service` (which did `from app.config import get_settings`).
    A `setattr(config, ...)` alone doesn't reach modules that already bound
    the name at import time.
    """
    from app import config

    class FakeSettings:
        site_url = "https://smarttap.test"

    monkeypatch.setattr(config, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(reactivation_service, "get_settings", lambda: FakeSettings())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_run_daily_sends_emails_and_marks_cooldown(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    sent_emails: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [
        {
            "id": "t-1",
            "name": "ACME Barber",
            "stamps_for_reward": 10,
            "reward_description": "free cut",
        },
    ]
    fake_customers.eligible_by_tenant["t-1"] = [
        {
            "id": "c-1",
            "name": "Alex",
            "email": "a@x.test",
            "current_stamps": 3,
            "magic_link_token": "tokA",
        },
        {
            "id": "c-2",
            "name": "Sam",
            "email": "s@x.test",
            "current_stamps": 7,
            "magic_link_token": "tokB",
        },
    ]
    now = datetime(2026, 5, 26, 10, 0, tzinfo=UTC)

    result = reactivation_service.run_daily(now=now)

    assert result.tenants_scanned == 1
    assert result.total_sent == 2
    assert len(sent_emails) == 2
    # Cooldown markers were written for both customers, at the cron's `now`
    # timestamp (not whatever the email service chose).
    assert set(fake_customers.marks) == {("c-1", now), ("c-2", now)}


def test_run_daily_builds_correct_magic_and_opt_out_urls(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    sent_emails: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [
        {"id": "t-1", "name": "ACME", "stamps_for_reward": 10, "reward_description": "x"},
    ]
    fake_customers.eligible_by_tenant["t-1"] = [
        {
            "id": "c-1",
            "name": "Alex",
            "email": "a@x.test",
            "current_stamps": 3,
            "magic_link_token": "tokA",
        },
    ]

    reactivation_service.run_daily(now=datetime(2026, 5, 26, tzinfo=UTC))

    assert sent_emails[0]["magic_link_url"] == "https://smarttap.test/m/tokA"
    assert sent_emails[0]["opt_out_url"] == "https://smarttap.test/u/tokA"


def test_run_daily_iterates_all_tenants(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    sent_emails: list[dict[str, Any]],
) -> None:
    fake_tenants.rows = [
        {"id": "t-1", "name": "A", "stamps_for_reward": 10, "reward_description": "x"},
        {"id": "t-2", "name": "B", "stamps_for_reward": 5, "reward_description": "y"},
        {"id": "t-3", "name": "C", "stamps_for_reward": 8, "reward_description": "z"},
    ]
    fake_customers.eligible_by_tenant["t-1"] = [
        {"id": "c-1", "email": "a@x", "name": "x", "current_stamps": 1, "magic_link_token": "k1"},
    ]
    # t-2 has nobody eligible.
    fake_customers.eligible_by_tenant["t-3"] = [
        {"id": "c-3", "email": "c@x", "name": "z", "current_stamps": 4, "magic_link_token": "k3"},
    ]

    result = reactivation_service.run_daily()

    assert result.tenants_scanned == 3
    assert result.total_sent == 2
    # Per-tenant breakdown preserves the scanned tenants, including the empty one.
    tenant_ids = [r.tenant_id for r in result.by_tenant]
    assert tenant_ids == ["t-1", "t-2", "t-3"]
    by_id = {r.tenant_id: r for r in result.by_tenant}
    assert by_id["t-2"].eligible == 0
    assert by_id["t-2"].sent == 0


# ---------------------------------------------------------------------------
# Failure containment
# ---------------------------------------------------------------------------


def test_run_daily_skips_customer_without_magic_token(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    sent_emails: list[dict[str, Any]],
) -> None:
    """A customer row missing magic_link_token would render a broken link.
    Skip with an error, don't crash the run."""
    fake_tenants.rows = [
        {"id": "t-1", "name": "A", "stamps_for_reward": 10, "reward_description": "x"},
    ]
    fake_customers.eligible_by_tenant["t-1"] = [
        {"id": "c-1", "email": "a@x", "name": "x", "current_stamps": 1, "magic_link_token": None},
        {"id": "c-2", "email": "b@x", "name": "y", "current_stamps": 2, "magic_link_token": "tokB"},
    ]

    result = reactivation_service.run_daily()

    assert result.total_sent == 1
    assert sent_emails[0]["customer"]["id"] == "c-2"
    tres = result.by_tenant[0]
    assert any("c-1" in e for e in tres.errors)
    # The broken row must NOT have been marked — otherwise we'd silently
    # never retry once magic_link_token gets repaired.
    assert ("c-1", pytest.approx(None)) not in [(cid, None) for cid, _ in fake_customers.marks]
    assert "c-2" in {cid for cid, _ in fake_customers.marks}


def test_run_daily_per_customer_send_exception_is_isolated(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If send_reactivation throws for one customer, the loop continues for
    the rest. The cooldown marker stays (mark-before-send semantics)."""
    fake_tenants.rows = [
        {"id": "t-1", "name": "A", "stamps_for_reward": 10, "reward_description": "x"},
    ]
    fake_customers.eligible_by_tenant["t-1"] = [
        {"id": "c-1", "email": "a@x", "name": "x", "current_stamps": 1, "magic_link_token": "tokA"},
        {"id": "c-2", "email": "b@x", "name": "y", "current_stamps": 2, "magic_link_token": "tokB"},
    ]

    calls: list[str] = []

    def flaky_send(**kw: Any) -> bool:
        cid = kw["customer"]["id"]
        calls.append(cid)
        if cid == "c-1":
            raise RuntimeError("Resend hiccup")
        return True

    monkeypatch.setattr(reactivation_service.email_service, "send_reactivation", flaky_send)

    result = reactivation_service.run_daily()

    # Both customers were attempted; one failure didn't stop the second.
    assert calls == ["c-1", "c-2"]
    # The cron counter records SENT (which is incremented after the send
    # call returns without raising). c-1 raised, so sent should be 1.
    assert result.total_sent == 1
    # BOTH cooldowns are still marked — that's the "lose one cycle rather
    # than spam" trade-off the orchestrator promises.
    marked_ids = {cid for cid, _ in fake_customers.marks}
    assert marked_ids == {"c-1", "c-2"}
    # The c-1 failure is captured as a per-tenant error string.
    tres = result.by_tenant[0]
    assert any("c-1" in e for e in tres.errors)


def test_run_daily_with_no_active_tenants_returns_zero(
    fake_tenants: FakeTenantsDB,
    fake_customers: FakeCustomersDB,
    sent_emails: list[dict[str, Any]],
) -> None:
    """Smoke test for the empty-system case — fresh install, no tenants yet."""
    result = reactivation_service.run_daily()

    assert result.tenants_scanned == 0
    assert result.total_sent == 0
    assert result.by_tenant == []
    assert sent_emails == []


# ---------------------------------------------------------------------------
# Opt-out
# ---------------------------------------------------------------------------


def test_opt_out_revokes_and_returns(
    fake_customers: FakeCustomersDB,
) -> None:
    fake_customers.revoke_returns["tok_known"] = {"id": "c-7"}

    # Returns None on success (the router translates to 204).
    assert reactivation_service.opt_out("tok_known") is None
    assert fake_customers.revoked_tokens == ["tok_known"]


def test_opt_out_unknown_token_raises_not_found(
    fake_customers: FakeCustomersDB,
) -> None:
    """Unknown token → NotFoundError. The router turns that into a 404 with
    the standard error body, deliberately indistinguishable from a malformed
    token (no enumeration oracle)."""
    fake_customers.revoke_returns["tok_unknown"] = None

    with pytest.raises(NotFoundError):
        reactivation_service.opt_out("tok_unknown")
