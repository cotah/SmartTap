"""Tests for multi-tenant selection via the X-Tenant-Id header.

Covers get_current_tenant_id (default first membership, valid override,
403 on non-membership) and GET /me returning all memberships plus the
active tenant resolved from the header.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import dependencies
from app.dependencies import CurrentUser, get_current_tenant_id, get_current_user
from app.main import app
from app.routers import me as me_router

client = TestClient(app)

USER = CurrentUser(user_id="user-1", email="owner@example.com")

MEMBERSHIPS = [
    {"tenant_id": "tenant-a", "user_id": "user-1", "role": "owner"},
    {"tenant_id": "tenant-b", "user_id": "user-1", "role": "owner"},
]


def _tenant(tenant_id: str, name: str) -> dict[str, Any]:
    return {
        "id": tenant_id,
        "slug": name.lower(),
        "name": name,
        "business_type": "restaurant",
        "plan": "trial",
        "is_active": True,
        "trial_ends_at": "2099-01-01T00:00:00+00:00",
        "reward_description": None,
        "enabled_modules": ["reviews"],
    }


@pytest.fixture
def _memberships(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dependencies.tenant_members, "list_for_user", lambda user_id: MEMBERSHIPS
    )


# --- get_current_tenant_id ---


def test_default_returns_first_membership(_memberships: None) -> None:
    assert get_current_tenant_id(USER, None) == "tenant-a"


def test_header_selects_other_membership(_memberships: None) -> None:
    assert get_current_tenant_id(USER, "tenant-b") == "tenant-b"


def test_header_non_membership_raises_403(_memberships: None) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_tenant_id(USER, "tenant-intruder")
    assert exc_info.value.status_code == 403


def test_no_memberships_raises_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies.tenant_members, "list_for_user", lambda user_id: [])
    with pytest.raises(HTTPException) as exc_info:
        get_current_tenant_id(USER, None)
    assert exc_info.value.status_code == 403


# --- GET /me ---


@pytest.fixture
def _me_setup(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    tenants_by_id = {
        "tenant-a": _tenant("tenant-a", "Yamamori"),
        "tenant-b": _tenant("tenant-b", "Panda"),
    }
    monkeypatch.setattr(
        me_router.tenant_members, "list_for_user", lambda user_id: MEMBERSHIPS
    )
    monkeypatch.setattr(
        me_router.tenants, "get_by_id", lambda tenant_id: tenants_by_id.get(tenant_id)
    )
    app.dependency_overrides[get_current_user] = lambda: USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_me_lists_all_tenants_and_defaults_to_first(_me_setup: None) -> None:
    resp = client.get("/v1/me")
    assert resp.status_code == 200
    body = resp.json()
    assert [t["id"] for t in body["tenants"]] == ["tenant-a", "tenant-b"]
    assert body["tenant"]["id"] == "tenant-a"


def test_me_header_switches_active_tenant(_me_setup: None) -> None:
    resp = client.get("/v1/me", headers={"X-Tenant-Id": "tenant-b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant"]["id"] == "tenant-b"
    assert [t["id"] for t in body["tenants"]] == ["tenant-a", "tenant-b"]


def test_me_invalid_header_falls_back_to_first(_me_setup: None) -> None:
    resp = client.get("/v1/me", headers={"X-Tenant-Id": "tenant-intruder"})
    assert resp.status_code == 200
    assert resp.json()["tenant"]["id"] == "tenant-a"
