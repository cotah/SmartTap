from typing import Any

import pytest

from app.services import stripe_client


def test_create_customer_returns_none_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stripe_client, "is_configured", lambda: False)

    result = stripe_client.create_customer(
        tenant_id="t-1",
        email="owner@example.com",
        name="ACME Barber",
    )
    assert result is None


def test_create_customer_passes_metadata_and_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeCustomer:
        @staticmethod
        def create(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"id": "cus_abc123"}

    monkeypatch.setattr(stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(stripe_client, "configure_stripe", lambda: None)
    monkeypatch.setattr(stripe_client.stripe, "Customer", FakeCustomer)

    result = stripe_client.create_customer(
        tenant_id="tenant-uuid-1",
        email="owner@example.com",
        name="ACME Barber",
    )

    assert result == "cus_abc123"
    assert captured["email"] == "owner@example.com"
    assert captured["name"] == "ACME Barber"
    assert captured["metadata"] == {"tenant_id": "tenant-uuid-1"}
    assert captured["idempotency_key"] == "tenant-tenant-uuid-1-create"
