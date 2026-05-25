from datetime import UTC, datetime
from typing import Any

import pytest

from app.services import onboarding_service
from app.services.onboarding_service import TRIAL_DAYS, bootstrap_owner


def _fake_tenant_create_factory() -> tuple[list[dict[str, Any]], Any]:
    created: list[dict[str, Any]] = []

    def fake_create(payload: dict[str, Any]) -> dict[str, Any]:
        row = {"id": f"t-{len(created) + 1}", **payload}
        created.append(row)
        return row

    return created, fake_create


def _wire_minimal(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stub the DB so bootstrap can run without Supabase. Returns the list of
    `tenants.create` payloads so tests can inspect them."""
    created, fake_create = _fake_tenant_create_factory()

    monkeypatch.setattr(
        onboarding_service.tenant_members, "list_for_user", lambda _uid: []
    )
    monkeypatch.setattr(
        onboarding_service.tenant_members,
        "create",
        lambda **_kw: {"id": "m-1"},
    )
    monkeypatch.setattr(onboarding_service.tenants, "get_by_slug", lambda _slug: None)
    monkeypatch.setattr(onboarding_service.tenants, "create", fake_create)

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        # Find the created row and merge.
        for row in created:
            if row["id"] == tenant_id:
                row.update(fields)
                return row
        raise AssertionError(f"unknown tenant_id {tenant_id}")

    monkeypatch.setattr(onboarding_service.tenants, "update", fake_update)
    return created


def test_bootstrap_creates_tenant_with_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    created = _wire_minimal(monkeypatch)
    monkeypatch.setattr(
        onboarding_service.stripe_client, "create_customer", lambda **_kw: None
    )

    result = bootstrap_owner(
        user_id="user-1", email="alice@example.com", business_name="ACME Barber"
    )

    assert result.is_new is True
    assert len(created) == 1
    row = created[0]
    assert row["plan"] == "trial"
    assert row["name"] == "ACME Barber"
    # trial_ends_at should be ~TRIAL_DAYS in the future.
    trial_ends = datetime.fromisoformat(row["trial_ends_at"])
    delta_days = (trial_ends - datetime.now(UTC)).total_seconds() / 86400
    assert TRIAL_DAYS - 1 < delta_days <= TRIAL_DAYS


def test_bootstrap_attaches_stripe_customer_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _wire_minimal(monkeypatch)
    stripe_calls: list[dict[str, Any]] = []

    def fake_create_customer(**kwargs: Any) -> str:
        stripe_calls.append(kwargs)
        return "cus_abc"

    monkeypatch.setattr(
        onboarding_service.stripe_client, "create_customer", fake_create_customer
    )

    result = bootstrap_owner(
        user_id="user-1", email="alice@example.com", business_name="ACME Barber"
    )

    assert len(stripe_calls) == 1
    assert stripe_calls[0]["email"] == "alice@example.com"
    assert stripe_calls[0]["name"] == "ACME Barber"
    assert stripe_calls[0]["tenant_id"] == created[0]["id"]
    assert result.tenant["stripe_customer_id"] == "cus_abc"


def test_bootstrap_succeeds_when_stripe_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wire_minimal(monkeypatch)
    monkeypatch.setattr(
        onboarding_service.stripe_client, "create_customer", lambda **_kw: None
    )

    result = bootstrap_owner(
        user_id="user-1", email="alice@example.com", business_name=None
    )

    assert result.is_new is True
    assert "stripe_customer_id" not in result.tenant
    assert result.tenant["name"] == "My business"


def test_bootstrap_succeeds_when_stripe_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wire_minimal(monkeypatch)

    def boom(**_kw: Any) -> str:
        raise RuntimeError("stripe down")

    monkeypatch.setattr(onboarding_service.stripe_client, "create_customer", boom)

    result = bootstrap_owner(
        user_id="user-1", email="alice@example.com", business_name=None
    )

    # Tenant still created, billing id absent — backfill later.
    assert result.is_new is True
    assert "stripe_customer_id" not in result.tenant


def test_bootstrap_returns_existing_tenant_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_tenant = {"id": "t-existing", "name": "Old", "plan": "pro"}
    monkeypatch.setattr(
        onboarding_service.tenant_members,
        "list_for_user",
        lambda _uid: [{"tenant_id": "t-existing"}],
    )
    monkeypatch.setattr(
        onboarding_service.tenants, "get_by_id", lambda _id: existing_tenant
    )

    def fail_create(*_a: Any, **_kw: Any) -> None:
        raise AssertionError("must not create tenant when membership exists")

    monkeypatch.setattr(onboarding_service.tenants, "create", fail_create)
    monkeypatch.setattr(
        onboarding_service.stripe_client, "create_customer", fail_create
    )

    result = bootstrap_owner(
        user_id="user-1", email="alice@example.com", business_name="Whatever"
    )
    assert result.is_new is False
    assert result.tenant is existing_tenant
