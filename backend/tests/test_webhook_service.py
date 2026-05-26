from typing import Any

import pytest

from app.services import webhook_service


@pytest.fixture(autouse=True)
def _silence_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Webhook tests assert on DB state; email triggers are a separate concern
    (covered in test_email_service.py). Stub them here so tests don't have
    to remember to do it individually."""
    _stub_emails(monkeypatch)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _settings(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    """Stub get_settings() so the price→plan reverse lookup has known IDs."""
    defaults = {
        "stripe_price_review": "price_recur_review",
        "stripe_price_loyalty": "price_recur_loyalty",
        "stripe_price_pro": "price_recur_pro",
        "stripe_price_network": "price_recur_network",
    }
    defaults.update(overrides)

    class FakeSettings:
        pass

    fake = FakeSettings()
    for k, v in defaults.items():
        setattr(fake, k, v)
    monkeypatch.setattr(webhook_service, "get_settings", lambda: fake)


def _stub_claim(monkeypatch: pytest.MonkeyPatch, *, returns: bool = True) -> list[tuple[str, str]]:
    """Replace stripe_events.claim. Returns the list of (event_id, type) it received."""
    calls: list[tuple[str, str]] = []

    def fake_claim(event_id: str, event_type: str, _payload: dict[str, Any]) -> bool:
        calls.append((event_id, event_type))
        return returns

    monkeypatch.setattr(webhook_service.stripe_events, "claim", fake_claim)
    return calls


def _stub_tenants(
    monkeypatch: pytest.MonkeyPatch,
    *,
    by_subscription: dict[str, dict[str, Any]] | None = None,
    by_customer: dict[str, dict[str, Any]] | None = None,
    by_id: dict[str, dict[str, Any]] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Replace tenants lookups + update. Returns the list of (tenant_id, fields)
    that update() was called with.

    `by_id` covers `tenants.get_by_id`, which post-S3-W7 handlers call to
    re-fetch the row before triggering an email. Tests that don't care about
    the email branch can leave it empty — the handler tolerates None."""
    by_subscription = by_subscription or {}
    by_customer = by_customer or {}
    by_id = by_id or {}

    updates: list[tuple[str, dict[str, Any]]] = []

    def fake_update(tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        updates.append((tenant_id, fields))
        return {"id": tenant_id, **fields}

    monkeypatch.setattr(webhook_service.tenants, "update", fake_update)
    monkeypatch.setattr(
        webhook_service.tenants,
        "get_by_stripe_subscription",
        lambda sid: by_subscription.get(sid),
    )
    monkeypatch.setattr(
        webhook_service.tenants,
        "get_by_stripe_customer",
        lambda cid: by_customer.get(cid),
    )
    monkeypatch.setattr(
        webhook_service.tenants,
        "get_by_id",
        lambda tid: by_id.get(tid),
    )
    return updates


def _stub_emails(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    """Replace every email_service.send_* with a no-op recorder.

    Webhooks must succeed regardless of email; tests assert the side-effect
    on the DB. The email-specific assertions live in test_email_service.py.
    Returned list contains (event_name, kwargs) for tests that want to peek."""
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake(name: str) -> Any:
        def _inner(**kwargs: Any) -> None:
            calls.append((name, kwargs))
        return _inner

    monkeypatch.setattr(
        webhook_service.email_service,
        "send_payment_succeeded",
        fake("payment_succeeded"),
    )
    monkeypatch.setattr(
        webhook_service.email_service,
        "send_payment_failed",
        fake("payment_failed"),
    )
    monkeypatch.setattr(
        webhook_service.email_service,
        "send_subscription_canceled",
        fake("subscription_canceled"),
    )
    return calls


def _event(event_type: str, obj: dict[str, Any], event_id: str = "evt_test_1") -> dict[str, Any]:
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_handle_short_circuits_when_event_already_processed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """claim() returning False means this event was already recorded; the
    handler must not be invoked a second time, regardless of event type."""
    _stub_claim(monkeypatch, returns=False)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "checkout.session.completed",
            {"id": "cs_x", "metadata": {"tenant_id": "t-1"}, "subscription": "sub_1"},
        )
    )

    assert updates == [], "tenant update must not run when event is a duplicate"


def test_handle_processes_event_when_claim_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    claim_calls = _stub_claim(monkeypatch, returns=True)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "checkout.session.completed",
            {"id": "cs_x", "metadata": {"tenant_id": "t-1"}, "subscription": "sub_1"},
            event_id="evt_abc",
        )
    )

    assert claim_calls == [("evt_abc", "checkout.session.completed")]
    assert len(updates) == 1
    assert updates[0][0] == "t-1"


# ---------------------------------------------------------------------------
# checkout.session.completed
# ---------------------------------------------------------------------------


def test_checkout_completed_links_subscription_and_activates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "checkout.session.completed",
            {
                "id": "cs_test_123",
                "metadata": {"tenant_id": "t-1"},
                "subscription": "sub_abc",
                "customer": "cus_abc",
            },
        )
    )

    assert updates == [
        (
            "t-1",
            {
                "stripe_subscription_id": "sub_abc",
                "is_active": True,
                "cancelled_at": None,
            },
        )
    ]


def test_checkout_completed_swallows_when_tenant_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No metadata + no DB row to fall back to → log and exit, do not raise.
    Raising would make Stripe retry forever on a permanent data issue."""
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)  # no by_subscription / by_customer mappings

    webhook_service.handle(
        _event(
            "checkout.session.completed",
            {
                "id": "cs_x",
                "metadata": {},
                "subscription": "sub_unknown",
                "customer": "cus_unknown",
            },
        )
    )

    assert updates == []


def test_checkout_completed_falls_back_to_subscription_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stripe dashboard-created sessions won't carry our metadata. The service
    must locate the tenant by subscription_id as a fallback."""
    _stub_claim(monkeypatch)
    updates = _stub_tenants(
        monkeypatch,
        by_subscription={"sub_existing": {"id": "t-7"}},
    )

    webhook_service.handle(
        _event(
            "checkout.session.completed",
            {"id": "cs_x", "metadata": {}, "subscription": "sub_existing", "customer": "cus_x"},
        )
    )

    assert updates and updates[0][0] == "t-7"


# ---------------------------------------------------------------------------
# customer.subscription.updated
# ---------------------------------------------------------------------------


def _subscription(
    *,
    status: str,
    price_id: str = "price_recur_loyalty",
    tenant_id: str | None = "t-1",
    sub_id: str = "sub_1",
    customer_id: str = "cus_1",
) -> dict[str, Any]:
    return {
        "id": sub_id,
        "status": status,
        "customer": customer_id,
        "metadata": {"tenant_id": tenant_id} if tenant_id else {},
        "items": {"data": [{"price": {"id": price_id}}]},
    }


def test_subscription_updated_active_sets_plan_and_activates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event("customer.subscription.updated", _subscription(status="active"))
    )

    assert len(updates) == 1
    tenant_id, fields = updates[0]
    assert tenant_id == "t-1"
    assert fields["is_active"] is True
    assert fields["plan"] == "loyalty"
    assert fields["cancelled_at"] is None
    assert fields["stripe_subscription_id"] == "sub_1"


def test_subscription_updated_trialing_treated_as_active(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "customer.subscription.updated",
            _subscription(status="trialing", price_id="price_recur_pro"),
        )
    )

    assert updates[0][1]["is_active"] is True
    assert updates[0][1]["plan"] == "pro"


def test_subscription_updated_canceled_deactivates_keeping_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decision #3: cancellation keeps `plan` for history/reactivation; only
    flips is_active to false and stamps cancelled_at."""
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "customer.subscription.updated",
            _subscription(status="canceled", price_id="price_recur_loyalty"),
        )
    )

    fields = updates[0][1]
    assert fields["is_active"] is False
    assert fields["cancelled_at"] is not None
    assert "plan" not in fields  # plan NOT overwritten on cancel


def test_subscription_updated_past_due_logs_without_state_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """past_due means Stripe is still retrying payment; don't deactivate yet."""
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event("customer.subscription.updated", _subscription(status="past_due"))
    )

    # update is still called (records subscription_id) but is_active/plan not set
    assert len(updates) == 1
    fields = updates[0][1]
    assert "is_active" not in fields
    assert "plan" not in fields


def test_subscription_updated_unknown_price_keeps_tenant_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A price_id we don't recognize (e.g. someone added a price in the
    dashboard) shouldn't deactivate a working tenant. Log + don't touch plan."""
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "customer.subscription.updated",
            _subscription(status="active", price_id="price_unknown_xyz"),
        )
    )

    fields = updates[0][1]
    assert fields["is_active"] is True
    assert "plan" not in fields


def test_subscription_updated_no_tenant_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "customer.subscription.updated",
            _subscription(status="active", tenant_id=None, sub_id="sub_orphan"),
        )
    )

    assert updates == []


# ---------------------------------------------------------------------------
# customer.subscription.deleted
# ---------------------------------------------------------------------------


def test_subscription_deleted_deactivates_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "customer.subscription.deleted",
            {"id": "sub_1", "metadata": {"tenant_id": "t-1"}, "customer": "cus_1"},
        )
    )

    tenant_id, fields = updates[0]
    assert tenant_id == "t-1"
    assert fields == {"is_active": False, "cancelled_at": fields["cancelled_at"]}
    assert fields["cancelled_at"] is not None


# ---------------------------------------------------------------------------
# invoice.* — observability only
# ---------------------------------------------------------------------------


def test_invoice_payment_succeeded_does_not_update_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """invoice events are observability only; subscription.* is the source of
    truth for state. Asserting no DB write protects against accidental scope
    creep here."""
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "invoice.payment_succeeded",
            {"id": "in_1", "customer": "cus_1", "amount_paid": 2900, "subscription": "sub_1"},
        )
    )

    assert updates == []


def test_invoice_payment_failed_does_not_update_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(
        _event(
            "invoice.payment_failed",
            {"id": "in_2", "customer": "cus_1", "amount_due": 2900, "attempt_count": 1},
        )
    )

    assert updates == []


# ---------------------------------------------------------------------------
# Unhandled event types
# ---------------------------------------------------------------------------


def test_handle_ignores_unknown_event_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even if Stripe sends us a type we didn't subscribe to, we must not
    raise. Claim it (so retries don't loop) and exit."""
    _stub_claim(monkeypatch)
    updates = _stub_tenants(monkeypatch)

    webhook_service.handle(_event("customer.created", {"id": "cus_new"}))

    assert updates == []


# ---------------------------------------------------------------------------
# Price-id reverse lookup
# ---------------------------------------------------------------------------


def test_plan_from_price_id_maps_each_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    _settings(monkeypatch)
    assert webhook_service._plan_from_price_id("price_recur_review") == "review"
    assert webhook_service._plan_from_price_id("price_recur_loyalty") == "loyalty"
    assert webhook_service._plan_from_price_id("price_recur_pro") == "pro"
    assert webhook_service._plan_from_price_id("price_recur_network") == "network"
    assert webhook_service._plan_from_price_id("price_random") is None
    assert webhook_service._plan_from_price_id(None) is None


def test_plan_from_price_id_ignores_unconfigured_plans(monkeypatch: pytest.MonkeyPatch) -> None:
    """When a plan price isn't set in env, it must not collide with an empty
    string lookup. Otherwise any unrecognized price '' would map to a plan."""
    _settings(
        monkeypatch,
        stripe_price_review="",
        stripe_price_loyalty="price_recur_loyalty",
        stripe_price_pro="",
        stripe_price_network="",
    )
    assert webhook_service._plan_from_price_id("") is None
    assert webhook_service._plan_from_price_id("price_recur_loyalty") == "loyalty"
