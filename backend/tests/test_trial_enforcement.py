"""Tests for the require_active_tenant dependency.

Rather than spin up the full FastAPI app + JWT machinery, we exercise the
dependency function directly with stubbed tenant rows. The route wiring
(which routes apply the dependency) is verified by inspecting the actual
router file in test_trial_route_wiring.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app import dependencies
from app.errors import NotFoundError, SubscriptionInactiveError, TrialExpiredError


def _tenant(
    *,
    plan: str = "trial",
    is_active: bool = True,
    trial_ends_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "id": "t-1",
        "plan": plan,
        "is_active": is_active,
        "trial_ends_at": trial_ends_at.isoformat() if trial_ends_at else None,
    }


def test_require_active_returns_id_for_active_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = _tenant(trial_ends_at=datetime.now(UTC) + timedelta(days=20))
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: tenant)

    assert dependencies.require_active_tenant("t-1") == "t-1"


def test_require_active_returns_id_for_subscribed_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant = _tenant(plan="loyalty", trial_ends_at=None)
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: tenant)

    assert dependencies.require_active_tenant("t-1") == "t-1"


def test_require_active_allows_expiring_soon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Amber state — tenant should still be able to edit. We only want to
    nudge them, not block them."""
    tenant = _tenant(trial_ends_at=datetime.now(UTC) + timedelta(days=3))
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: tenant)

    assert dependencies.require_active_tenant("t-1") == "t-1"


def test_require_active_raises_402_on_expired_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = _tenant(trial_ends_at=datetime.now(UTC) - timedelta(hours=1))
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: tenant)

    with pytest.raises(TrialExpiredError) as ei:
        dependencies.require_active_tenant("t-1")
    assert ei.value.status_code == 402
    assert ei.value.code == "trial_expired"


def test_require_active_raises_402_on_inactive_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelled subscription (is_active=false) blocks edits the same way an
    expired trial does — different error code so the UI can word it correctly."""
    tenant = _tenant(plan="loyalty", is_active=False)
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: tenant)

    with pytest.raises(SubscriptionInactiveError) as ei:
        dependencies.require_active_tenant("t-1")
    assert ei.value.status_code == 402
    assert ei.value.code == "subscription_inactive"


def test_require_active_raises_404_when_tenant_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dependencies.tenants, "get_by_id", lambda _id: None)

    with pytest.raises(NotFoundError):
        dependencies.require_active_tenant("missing")


# ---------------------------------------------------------------------------
# Route wiring — which routers actually apply the gate
# ---------------------------------------------------------------------------


def _routes_using(dependency_fn: Any, router: Any) -> list[str]:
    """Returns the list of route paths whose deps include `dependency_fn`.
    Walks FastAPI's compiled dependant tree, not the decorator source, so it
    survives refactors as long as the dependency is actually applied."""
    paths: list[str] = []
    for route in router.routes:
        if not hasattr(route, "dependant"):
            continue
        # flatten direct and nested dependencies
        stack = list(route.dependant.dependencies)
        seen: set[int] = set()
        while stack:
            dep = stack.pop()
            if id(dep) in seen:
                continue
            seen.add(id(dep))
            if dep.call is dependency_fn:
                paths.append(route.path)
                break
            stack.extend(dep.dependencies)
    return paths


def test_mutation_routes_are_gated() -> None:
    """The two dashboard mutation routes in S3-W5 scope MUST require an
    active tenant. If a future PR drops the dep, this test catches it."""
    from app.routers import tenants as tenants_router

    gated = _routes_using(dependencies.require_active_tenant, tenants_router.router)
    assert "/tenant/settings" in gated
    assert "/tenant/reward-config" in gated


def test_read_only_and_public_routes_not_gated() -> None:
    """Reverse guarantee: the gate must NOT be on read routes, billing,
    webhooks, public NFC endpoints, or onboarding. Locking any of these
    would break customer-facing flows or paying users' ability to recover."""
    from app.routers import billing, customers, onboarding, rewards, taps, webhooks
    from app.routers import tenants as tenants_router

    must_not_be_gated = [
        # billing — user needs it to escape the gate by paying
        billing.router,
        # webhooks — Stripe is not authenticated as a tenant
        webhooks.router,
        # public NFC — end customers must keep tapping
        taps.router,
        # reward validation — happens at the counter, must not require active tenant
        rewards.router,
        # customer identify is on customers.router (POST /customers/identify)
        customers.router,
        # onboarding — first-time setup, even after trial timer started
        onboarding.router,
    ]
    for r in must_not_be_gated:
        gated = _routes_using(dependencies.require_active_tenant, r)
        assert gated == [], f"router unexpectedly gated: {gated}"

    # GET /tenant must NOT be gated — only the mutation routes are.
    gated_tenants = _routes_using(dependencies.require_active_tenant, tenants_router.router)
    assert "/tenant" not in gated_tenants
