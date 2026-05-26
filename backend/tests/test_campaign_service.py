from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.errors import NotFoundError
from app.services import campaign_service
from app.services.campaign_service import (
    CampaignLockedError,
    ConflictingCampaignError,
    InvalidCampaignError,
    change_status,
    create_double_stamp,
    update_campaign,
)

# ---------------------------------------------------------------------------
# Test scaffolding — stub the DB to keep tests fast and deterministic
# ---------------------------------------------------------------------------


class FakeCampaignsDB:
    """Records inserts/updates and answers lookups. Simulates the uniqueness
    constraint enforced by the service layer (one active double_stamp per
    tenant) so tests don't accidentally pass just because the DB stub is loose."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": f"camp-{self._next_id}",
            "created_at": "2026-05-26T10:00:00+00:00",
            **fields,
        }
        self._next_id += 1
        self.rows.append(row)
        return row

    def get_by_id(self, campaign_id: str) -> dict[str, Any] | None:
        for r in self.rows:
            if r["id"] == campaign_id:
                return r
        return None

    def update(self, campaign_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        for r in self.rows:
            if r["id"] == campaign_id:
                r.update(fields)
                return r
        raise ValueError(f"campaign {campaign_id} not updated")

    def has_other_active_double_stamp(
        self, tenant_id: str, excluding_id: str | None = None
    ) -> bool:
        for r in self.rows:
            if r["tenant_id"] != tenant_id:
                continue
            if r["type"] != "double_stamp":
                continue
            if r["status"] != "active":
                continue
            if excluding_id is not None and r["id"] == excluding_id:
                continue
            return True
        return False


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeCampaignsDB:
    fake = FakeCampaignsDB()
    monkeypatch.setattr(campaign_service.campaigns, "create", fake.create)
    monkeypatch.setattr(campaign_service.campaigns, "get_by_id", fake.get_by_id)
    monkeypatch.setattr(campaign_service.campaigns, "update", fake.update)
    monkeypatch.setattr(
        campaign_service.campaigns,
        "has_other_active_double_stamp",
        fake.has_other_active_double_stamp,
    )
    return fake


def _future_window(*, days_ahead: int = 0, length_days: int = 7) -> tuple[datetime, datetime]:
    starts = datetime.now(UTC) + timedelta(days=days_ahead)
    return starts, starts + timedelta(days=length_days)


# ---------------------------------------------------------------------------
# create_double_stamp — validations
# ---------------------------------------------------------------------------


def test_create_happy_path_stores_config(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Weekend boost",
        multiplier=3,
        starts_at=starts,
        ends_at=ends,
    )
    assert row["type"] == "double_stamp"
    assert row["status"] == "draft"
    assert row["config"] == {"multiplier": 3}
    assert row["name"] == "Weekend boost"


def test_create_strips_whitespace_in_name(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="   Padded name   ",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
    )
    assert row["name"] == "Padded name"


@pytest.mark.parametrize("bad_name", ["", " ", "a", "   x   "])
def test_create_rejects_short_names(db: FakeCampaignsDB, bad_name: str) -> None:
    starts, ends = _future_window()
    with pytest.raises(InvalidCampaignError):
        create_double_stamp(
            tenant_id="t-1",
            name=bad_name,
            multiplier=2,
            starts_at=starts,
            ends_at=ends,
        )


@pytest.mark.parametrize("multiplier", [1, 0, -1, 6, 100])
def test_create_rejects_out_of_range_multiplier(
    db: FakeCampaignsDB, multiplier: int
) -> None:
    starts, ends = _future_window()
    with pytest.raises(InvalidCampaignError):
        create_double_stamp(
            tenant_id="t-1",
            name="Promo X",
            multiplier=multiplier,
            starts_at=starts,
            ends_at=ends,
        )


def test_create_rejects_inverted_window(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    with pytest.raises(InvalidCampaignError):
        create_double_stamp(
            tenant_id="t-1",
            name="Bad window",
            multiplier=2,
            starts_at=ends,  # swapped
            ends_at=starts,
        )


def test_create_rejects_zero_length_window(db: FakeCampaignsDB) -> None:
    """starts_at == ends_at is meaningless and would make every tap miss
    the window. Reject explicitly so the owner notices."""
    starts, _ = _future_window()
    with pytest.raises(InvalidCampaignError):
        create_double_stamp(
            tenant_id="t-1",
            name="Zero",
            multiplier=2,
            starts_at=starts,
            ends_at=starts,
        )


# ---------------------------------------------------------------------------
# Uniqueness: one active double_stamp per tenant
# ---------------------------------------------------------------------------


def test_create_active_blocks_when_another_is_already_active(
    db: FakeCampaignsDB,
) -> None:
    starts, ends = _future_window()
    create_double_stamp(
        tenant_id="t-1",
        name="First",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    with pytest.raises(ConflictingCampaignError):
        create_double_stamp(
            tenant_id="t-1",
            name="Second",
            multiplier=3,
            starts_at=starts,
            ends_at=ends,
            status="active",
        )


def test_create_draft_does_not_check_uniqueness(db: FakeCampaignsDB) -> None:
    """Multiple drafts are fine — the owner is just planning. The conflict
    only matters when someone goes live."""
    starts, ends = _future_window()
    create_double_stamp(
        tenant_id="t-1",
        name="Active",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    # Drafts coexist freely.
    create_double_stamp(
        tenant_id="t-1",
        name="Draft A",
        multiplier=3,
        starts_at=starts,
        ends_at=ends,
    )
    create_double_stamp(
        tenant_id="t-1",
        name="Draft B",
        multiplier=4,
        starts_at=starts,
        ends_at=ends,
    )
    assert len(db.rows) == 3


def test_uniqueness_is_per_tenant(db: FakeCampaignsDB) -> None:
    """Tenant A having an active campaign must not block tenant B."""
    starts, ends = _future_window()
    create_double_stamp(
        tenant_id="t-A",
        name="A1",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    create_double_stamp(
        tenant_id="t-B",
        name="B1",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    assert len(db.rows) == 2


# ---------------------------------------------------------------------------
# update_campaign — only draft is editable
# ---------------------------------------------------------------------------


def test_update_draft_changes_fields(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Original",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
    )

    new_ends = ends + timedelta(days=7)
    updated = update_campaign(
        tenant_id="t-1",
        campaign_id=row["id"],
        name="Updated",
        multiplier=4,
        ends_at=new_ends,
    )
    assert updated["name"] == "Updated"
    assert updated["config"] == {"multiplier": 4}
    assert updated["ends_at"] == new_ends.isoformat()


def test_update_active_campaign_is_locked(db: FakeCampaignsDB) -> None:
    """Decision #6: edits require pausing first. Otherwise mid-campaign
    multiplier changes confuse customers and break stamp math."""
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Live",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    with pytest.raises(CampaignLockedError):
        update_campaign(tenant_id="t-1", campaign_id=row["id"], multiplier=3)


def test_update_validates_window_with_old_value_when_only_one_changes(
    db: FakeCampaignsDB,
) -> None:
    """If user updates only ends_at, validation should use the stored
    starts_at so it can still catch ends < starts."""
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Promo X",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
    )
    # Try to set ends_at before the original starts_at.
    with pytest.raises(InvalidCampaignError):
        update_campaign(
            tenant_id="t-1",
            campaign_id=row["id"],
            ends_at=starts - timedelta(days=1),
        )


def test_update_cross_tenant_is_not_found(db: FakeCampaignsDB) -> None:
    """A user from tenant B must not be able to mutate tenant A's campaign,
    even if they somehow know the id."""
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-A",
        name="Promo A",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
    )
    with pytest.raises(NotFoundError):
        update_campaign(
            tenant_id="t-B",
            campaign_id=row["id"],
            name="hijacked",
        )


# ---------------------------------------------------------------------------
# change_status — state machine
# ---------------------------------------------------------------------------


def test_status_transition_draft_to_active(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Promo X",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
    )
    updated = change_status(tenant_id="t-1", campaign_id=row["id"], new_status="active")
    assert updated["status"] == "active"


def test_status_transition_blocks_second_activation(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    a = create_double_stamp(
        tenant_id="t-1",
        name="Promo A",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    assert a["status"] == "active"
    b = create_double_stamp(
        tenant_id="t-1",
        name="Promo B",
        multiplier=3,
        starts_at=starts,
        ends_at=ends,
    )
    with pytest.raises(ConflictingCampaignError):
        change_status(tenant_id="t-1", campaign_id=b["id"], new_status="active")


def test_status_transition_active_to_paused_clears_uniqueness_slot(
    db: FakeCampaignsDB,
) -> None:
    """After pausing the active one, the next can be activated. Important —
    it's the standard "swap to a new promotion" flow."""
    starts, ends = _future_window()
    a = create_double_stamp(
        tenant_id="t-1",
        name="Promo A",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    b = create_double_stamp(
        tenant_id="t-1",
        name="Promo B",
        multiplier=3,
        starts_at=starts,
        ends_at=ends,
    )
    change_status(tenant_id="t-1", campaign_id=a["id"], new_status="paused")
    updated_b = change_status(tenant_id="t-1", campaign_id=b["id"], new_status="active")
    assert updated_b["status"] == "active"


def test_ended_status_is_terminal(db: FakeCampaignsDB) -> None:
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Promo X",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    change_status(tenant_id="t-1", campaign_id=row["id"], new_status="ended")
    with pytest.raises(CampaignLockedError):
        change_status(tenant_id="t-1", campaign_id=row["id"], new_status="active")


def test_status_change_to_same_status_is_noop(db: FakeCampaignsDB) -> None:
    """Idempotent — clicking pause twice from a flaky frontend shouldn't error."""
    starts, ends = _future_window()
    row = create_double_stamp(
        tenant_id="t-1",
        name="Promo X",
        multiplier=2,
        starts_at=starts,
        ends_at=ends,
        status="active",
    )
    updated = change_status(
        tenant_id="t-1", campaign_id=row["id"], new_status="active"
    )
    assert updated["status"] == "active"
