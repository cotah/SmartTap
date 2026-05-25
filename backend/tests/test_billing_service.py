from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import billing_service
from app.services.billing_service import (
    BillingNotConfiguredError,
    MissingPriceError,
    create_checkout_session,
)


def _settings_with_prices(monkeypatch: pytest.MonkeyPatch, **prices: str) -> None:
    """Replace get_settings() with a stub carrying just the price fields the test
    needs. Defaults all configured plans to non-empty strings."""
    defaults = {
        "stripe_price_review": "price_recur_review",
        "stripe_price_loyalty": "price_recur_loyalty",
        "stripe_price_pro": "price_recur_pro",
        "stripe_price_network": "price_recur_network",
        "stripe_price_review_setup": "price_setup_review",
        "stripe_price_loyalty_setup": "price_setup_loyalty",
        "stripe_price_pro_setup": "price_setup_pro",
        "stripe_price_network_setup": "price_setup_network",
    }
    defaults.update(prices)

    class FakeSettings:
        pass

    fake = FakeSettings()
    for key, value in defaults.items():
        setattr(fake, key, value)

    monkeypatch.setattr(billing_service, "get_settings", lambda: fake)


def test_create_checkout_raises_when_stripe_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: False)
    with pytest.raises(BillingNotConfiguredError):
        create_checkout_session(
            tenant_id="t-1",
            plan="review",
            email="owner@example.com",
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )


def test_create_checkout_raises_when_tenant_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(billing_service.tenants, "get_by_id", lambda _id: None)
    with pytest.raises(NotFoundError):
        create_checkout_session(
            tenant_id="missing",
            plan="review",
            email=None,
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )


def test_create_checkout_raises_when_plan_price_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "name": "ACME", "stripe_customer_id": "cus_x"},
    )
    _settings_with_prices(monkeypatch, stripe_price_review="", stripe_price_review_setup="")

    with pytest.raises(MissingPriceError):
        create_checkout_session(
            tenant_id="t-1",
            plan="review",
            email=None,
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )


def test_create_checkout_happy_path_passes_correct_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {
            "id": "t-1",
            "name": "ACME Barber",
            "stripe_customer_id": "cus_existing",
        },
    )
    _settings_with_prices(monkeypatch)

    def fake_create(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "https://checkout.stripe.com/c/pay/cs_test_abc"

    monkeypatch.setattr(
        billing_service.stripe_client, "create_checkout_session", fake_create
    )

    url = create_checkout_session(
        tenant_id="t-1",
        plan="loyalty",
        email="owner@example.com",
        success_url="https://app.example/ok",
        cancel_url="https://app.example/cancel",
    )

    assert url.startswith("https://checkout.stripe.com/")
    assert captured["customer_id"] == "cus_existing"
    assert captured["tenant_id"] == "t-1"
    assert captured["recurring_price_id"] == "price_recur_loyalty"
    assert captured["setup_price_id"] == "price_setup_loyalty"
    assert captured["success_url"] == "https://app.example/ok"
    assert captured["cancel_url"] == "https://app.example/cancel"


def test_create_checkout_backfills_stripe_customer_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenants from W1 that booted without Stripe configured can upgrade later;
    the service must lazily create the Stripe Customer and persist it."""
    update_calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "name": "ACME", "stripe_customer_id": None},
    )
    monkeypatch.setattr(
        billing_service.tenants,
        "update",
        lambda tenant_id, fields: update_calls.append((tenant_id, fields))
        or {"id": tenant_id, **fields},
    )
    monkeypatch.setattr(
        billing_service.stripe_client,
        "create_customer",
        lambda **_kw: "cus_new",
    )
    _settings_with_prices(monkeypatch)

    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        billing_service.stripe_client,
        "create_checkout_session",
        lambda **kw: captured.update(kw) or "https://checkout.stripe.com/c/pay/cs_y",
    )

    create_checkout_session(
        tenant_id="t-1",
        plan="pro",
        email="owner@example.com",
        success_url="https://app.example/ok",
        cancel_url="https://app.example/cancel",
    )

    assert update_calls == [("t-1", {"stripe_customer_id": "cus_new"})]
    assert captured["customer_id"] == "cus_new"


def test_create_checkout_raises_when_create_customer_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """is_configured() said yes but create_customer returned None (race or
    misconfig). Don't continue with a None customer id."""
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "name": "ACME", "stripe_customer_id": None},
    )
    monkeypatch.setattr(
        billing_service.stripe_client, "create_customer", lambda **_kw: None
    )

    with pytest.raises(BillingNotConfiguredError):
        create_checkout_session(
            tenant_id="t-1",
            plan="review",
            email=None,
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )


def test_create_checkout_recovers_from_stale_customer_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Stripe says 'No such customer' for the stored id (typical after
    switching live <-> test keys), the service must wipe the stored id, create
    a fresh customer, and retry once. The caller never sees the error."""
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    _settings_with_prices(monkeypatch)

    # First get returns the stale id; after `tenants.update` is called, the
    # second get returns the row with stripe_customer_id cleared.
    tenant_state: dict[str, Any] = {
        "id": "t-1",
        "name": "ACME",
        "stripe_customer_id": "cus_stale_from_live",
    }
    monkeypatch.setattr(billing_service.tenants, "get_by_id", lambda _id: tenant_state)

    update_calls: list[tuple[str, dict[str, Any]]] = []

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        update_calls.append((tenant_id, fields))
        tenant_state.update(fields)
        return dict(tenant_state)

    monkeypatch.setattr(billing_service.tenants, "update", fake_update)

    create_customer_calls: list[dict[str, Any]] = []

    def fake_create_customer(**kwargs: Any) -> str:
        create_customer_calls.append(kwargs)
        return "cus_fresh_in_test"

    monkeypatch.setattr(
        billing_service.stripe_client, "create_customer", fake_create_customer
    )

    checkout_calls: list[dict[str, Any]] = []

    def fake_checkout(**kwargs: Any) -> str:
        checkout_calls.append(kwargs)
        if kwargs["customer_id"] == "cus_stale_from_live":
            raise Exception("No such customer: 'cus_stale_from_live'")
        return "https://checkout.stripe.com/c/pay/cs_test_recovered"

    monkeypatch.setattr(
        billing_service.stripe_client, "create_checkout_session", fake_checkout
    )

    url = create_checkout_session(
        tenant_id="t-1",
        plan="review",
        email="owner@example.com",
        success_url="https://app.example/ok",
        cancel_url="https://app.example/cancel",
    )

    assert url.endswith("cs_test_recovered")
    # DB was reset between the failed and successful attempt.
    assert update_calls[0] == ("t-1", {"stripe_customer_id": None})
    # Two checkout attempts: stale customer fails, fresh customer succeeds.
    assert [c["customer_id"] for c in checkout_calls] == [
        "cus_stale_from_live",
        "cus_fresh_in_test",
    ]
    # Exactly one fresh-customer creation triggered.
    assert len(create_customer_calls) == 1


def test_create_checkout_does_not_loop_on_repeated_stale_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If even the freshly created customer triggers 'No such customer'
    (something is deeply broken — e.g. wrong Stripe account entirely),
    the service must not retry forever. One retry, then propagate."""
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    _settings_with_prices(monkeypatch)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "name": "ACME", "stripe_customer_id": "cus_a"},
    )
    # update() returns the row with stripe_customer_id cleared, as the real
    # impl does.
    monkeypatch.setattr(
        billing_service.tenants,
        "update",
        lambda _tid, _fields: {"id": "t-1", "name": "ACME", "stripe_customer_id": None},
    )
    monkeypatch.setattr(
        billing_service.stripe_client, "create_customer", lambda **_kw: "cus_b"
    )

    attempts: list[str] = []

    def always_fails(**kwargs: Any) -> str:
        attempts.append(kwargs["customer_id"])
        raise Exception("No such customer: 'whatever'")

    monkeypatch.setattr(
        billing_service.stripe_client, "create_checkout_session", always_fails
    )

    with pytest.raises(Exception) as ei:
        create_checkout_session(
            tenant_id="t-1",
            plan="review",
            email=None,
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )

    assert "No such customer" in str(ei.value)
    # Exactly two attempts: original + one retry. No more.
    assert attempts == ["cus_a", "cus_b"]


def test_create_checkout_propagates_unrelated_stripe_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-'No such customer' Stripe error must NOT trigger the recovery
    path — we'd hide real bugs."""
    monkeypatch.setattr(billing_service.stripe_client, "is_configured", lambda: True)
    _settings_with_prices(monkeypatch)
    monkeypatch.setattr(
        billing_service.tenants,
        "get_by_id",
        lambda _id: {"id": "t-1", "name": "ACME", "stripe_customer_id": "cus_a"},
    )

    def reset_must_not_be_called(*_a: Any, **_kw: Any) -> None:
        raise AssertionError("tenants.update must not be called for unrelated errors")

    monkeypatch.setattr(billing_service.tenants, "update", reset_must_not_be_called)

    def fake_checkout(**_kw: Any) -> str:
        raise Exception("No such price: 'price_typo'")

    monkeypatch.setattr(
        billing_service.stripe_client, "create_checkout_session", fake_checkout
    )

    with pytest.raises(Exception) as ei:
        create_checkout_session(
            tenant_id="t-1",
            plan="review",
            email=None,
            success_url="https://app.example/ok",
            cancel_url="https://app.example/cancel",
        )
    assert "No such price" in str(ei.value)
