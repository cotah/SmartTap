"""Tests for the NFC tag service (S5-W0).

The interesting risks here:

    1. Tenant isolation — same anti-enumeration pattern as segments.
    2. `is_active` toggle — must NOT touch other fields. A merchant
       deactivating a tag should not accidentally rename it.
    3. `location_name` normalisation — whitespace-only input should
       store NULL so the dashboard's "<format> · <color>" fallback
       triggers, not a blank string.
    4. `location_name_explicitly_set` flag — distinguishes "left
       unchanged" from "cleared". A regression that conflated the two
       would silently wipe locations on every other patch.

DB layer is stubbed in-memory; the schema layer (Literal constraints) is
exercised through Pydantic when the router runs but doesn't need a unit
test here — Pydantic-rejected inputs never reach this service.
"""

from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import nfc_tag_service
from app.services.nfc_tag_service import create_tag, update_tag

# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class FakeNfcTagsDB:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1
        self._next_uuid = 1

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": f"tag-{self._next_id}",
            # Mimic the DB default — auto-generated, never accepted from
            # the caller.
            "tag_uuid": f"uuid-{self._next_uuid:08x}",
            "deployed_at": None,
            "created_at": "2026-05-26T10:00:00+00:00",
            **fields,
        }
        self._next_id += 1
        self._next_uuid += 1
        self.rows.append(row)
        return row

    def get_by_id(self, tag_id: str) -> dict[str, Any] | None:
        for r in self.rows:
            if r["id"] == tag_id:
                return r
        return None

    def update(self, tag_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        for r in self.rows:
            if r["id"] == tag_id:
                r.update(fields)
                return r
        raise ValueError(f"tag {tag_id} not updated")

    def list_for_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        return [r for r in self.rows if r["tenant_id"] == tenant_id]


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeNfcTagsDB:
    fake = FakeNfcTagsDB()
    monkeypatch.setattr(nfc_tag_service.nfc_tags, "create", fake.create)
    monkeypatch.setattr(nfc_tag_service.nfc_tags, "get_by_id", fake.get_by_id)
    monkeypatch.setattr(nfc_tag_service.nfc_tags, "update", fake.update)
    monkeypatch.setattr(
        nfc_tag_service.nfc_tags, "list_for_tenant", fake.list_for_tenant
    )
    return fake


# ---------------------------------------------------------------------------
# create_tag
# ---------------------------------------------------------------------------


def test_create_tag_defaults_to_active(db: FakeNfcTagsDB) -> None:
    row = create_tag(
        tenant_id="t-1",
        format="counter_stand",
        color="black",
        location_name="Front desk",
    )
    assert row["is_active"] is True
    assert row["format"] == "counter_stand"
    assert row["color"] == "black"
    assert row["location_name"] == "Front desk"
    assert row["tenant_id"] == "t-1"
    # Caller never controls tag_uuid — DB default does.
    assert row["tag_uuid"].startswith("uuid-")


def test_create_tag_trims_location_name(db: FakeNfcTagsDB) -> None:
    row = create_tag(
        tenant_id="t-1",
        format="table_tent",
        color="white",
        location_name="  Bar  ",
    )
    assert row["location_name"] == "Bar"


def test_create_tag_whitespace_only_location_becomes_null(
    db: FakeNfcTagsDB,
) -> None:
    """An all-whitespace input is effectively unset — store NULL so the
    dashboard's fallback label kicks in rather than rendering a blank
    string where the name should be."""
    row = create_tag(
        tenant_id="t-1",
        format="sticker",
        color="red",
        location_name="   ",
    )
    assert row["location_name"] is None


def test_create_tag_none_location_stays_none(db: FakeNfcTagsDB) -> None:
    row = create_tag(
        tenant_id="t-1",
        format="wall_plaque",
        color="navy",
        location_name=None,
    )
    assert row["location_name"] is None


# ---------------------------------------------------------------------------
# get_owned — anti-enumeration
# ---------------------------------------------------------------------------


def test_get_owned_returns_row_for_owning_tenant(db: FakeNfcTagsDB) -> None:
    row = create_tag(
        tenant_id="t-1",
        format="counter_stand",
        color="black",
        location_name=None,
    )
    fetched = nfc_tag_service.get_owned("t-1", row["id"])
    assert fetched["id"] == row["id"]


def test_get_owned_rejects_cross_tenant_lookup(db: FakeNfcTagsDB) -> None:
    """Owner of t-1 must not see t-2's tag — 404 (not 403) so the response
    doesn't leak existence."""
    create_tag(
        tenant_id="t-2",
        format="counter_stand",
        color="black",
        location_name=None,
    )
    with pytest.raises(NotFoundError):
        nfc_tag_service.get_owned("t-1", "tag-1")


def test_get_owned_unknown_id_raises_not_found(db: FakeNfcTagsDB) -> None:
    with pytest.raises(NotFoundError):
        nfc_tag_service.get_owned("t-1", "tag-does-not-exist")


# ---------------------------------------------------------------------------
# update_tag
# ---------------------------------------------------------------------------


def test_update_tag_changes_only_sent_fields(db: FakeNfcTagsDB) -> None:
    row = create_tag(
        tenant_id="t-1",
        format="counter_stand",
        color="black",
        location_name="Front desk",
    )
    updated = update_tag(
        tenant_id="t-1",
        tag_id=row["id"],
        color="navy",
    )
    assert updated["color"] == "navy"
    # Untouched fields keep their previous values.
    assert updated["format"] == "counter_stand"
    assert updated["location_name"] == "Front desk"


def test_update_tag_toggle_active_preserves_other_fields(
    db: FakeNfcTagsDB,
) -> None:
    """Critical — deactivating a tag must not accidentally rename it or
    flip its colour. A regression that conflated all fields would be
    invisible until a merchant complained their stand changed colour
    after a deactivation."""
    row = create_tag(
        tenant_id="t-1",
        format="table_tent",
        color="red",
        location_name="Bar",
    )
    updated = update_tag(
        tenant_id="t-1",
        tag_id=row["id"],
        is_active=False,
    )
    assert updated["is_active"] is False
    assert updated["format"] == "table_tent"
    assert updated["color"] == "red"
    assert updated["location_name"] == "Bar"


def test_update_tag_clear_location_name_when_explicitly_set(
    db: FakeNfcTagsDB,
) -> None:
    """Caller sends `location_name=None` AND flags it as explicit → clear
    the column. Mirrors the router's `model_fields_set` derivation."""
    row = create_tag(
        tenant_id="t-1",
        format="sticker",
        color="yellow",
        location_name="Cashier",
    )
    updated = update_tag(
        tenant_id="t-1",
        tag_id=row["id"],
        location_name=None,
        location_name_explicitly_set=True,
    )
    assert updated["location_name"] is None


def test_update_tag_omit_location_name_keeps_existing(
    db: FakeNfcTagsDB,
) -> None:
    """Caller doesn't send the field at all (the default — flag stays
    False) → keep the existing name. This is the most important branch:
    a regression here would silently wipe locations on every other
    patch."""
    row = create_tag(
        tenant_id="t-1",
        format="sticker",
        color="yellow",
        location_name="Cashier",
    )
    updated = update_tag(
        tenant_id="t-1",
        tag_id=row["id"],
        color="purple",
        # location_name not passed; flag stays False
    )
    assert updated["color"] == "purple"
    assert updated["location_name"] == "Cashier"


def test_update_tag_clear_location_via_whitespace(
    db: FakeNfcTagsDB,
) -> None:
    """If the caller sends whitespace-only with the explicit flag, treat
    it the same as None — store NULL."""
    row = create_tag(
        tenant_id="t-1",
        format="sticker",
        color="yellow",
        location_name="Cashier",
    )
    updated = update_tag(
        tenant_id="t-1",
        tag_id=row["id"],
        location_name="   ",
        location_name_explicitly_set=True,
    )
    assert updated["location_name"] is None


def test_update_tag_no_op_returns_current_row(db: FakeNfcTagsDB) -> None:
    """Sending no fields at all should still return the latest row so the
    API contract stays uniform."""
    row = create_tag(
        tenant_id="t-1",
        format="counter_stand",
        color="black",
        location_name="Desk",
    )
    result = update_tag(tenant_id="t-1", tag_id=row["id"])
    assert result["id"] == row["id"]
    assert result["format"] == "counter_stand"


def test_update_tag_rejects_cross_tenant(db: FakeNfcTagsDB) -> None:
    create_tag(
        tenant_id="t-2",
        format="counter_stand",
        color="black",
        location_name=None,
    )
    with pytest.raises(NotFoundError):
        update_tag(tenant_id="t-1", tag_id="tag-1", color="navy")
