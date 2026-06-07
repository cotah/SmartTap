"""Tests for the segment service (S4-W4).

The interesting risks here are:

    1. Tenant isolation — get_owned must reject cross-tenant ids the same
       way it rejects missing ones (no enumeration oracle).
    2. Criteria validation — the schema layer enforces shape; the service
       layer composes the runtime "now" cutoff. Both flows need coverage.
    3. Day → datetime translation — `last_visit_after_days: 30` against a
       known `now` must produce exactly `now - 30 days`. Off-by-one here
       would silently skew "recent" / "dormant" segments.

The DB layer is stubbed with an in-memory fake so each test isolates a
single behaviour.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.errors import NotFoundError
from app.schemas.segment import SegmentCriteria
from app.services import segment_service
from app.services.segment_service import (
    InvalidSegmentError,
    create_segment,
    delete_segment,
    evaluate,
    evaluate_unsaved,
    list_for_tenant_with_counts,
    update_segment,
)

# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class FakeSegmentsDB:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._next_id = 1

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": f"seg-{self._next_id}",
            "created_at": "2026-05-26T10:00:00+00:00",
            "updated_at": "2026-05-26T10:00:00+00:00",
            **fields,
        }
        self._next_id += 1
        self.rows.append(row)
        return row

    def get_by_id(self, segment_id: str) -> dict[str, Any] | None:
        for r in self.rows:
            if r["id"] == segment_id:
                return r
        return None

    def update(self, segment_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        for r in self.rows:
            if r["id"] == segment_id:
                r.update(fields)
                r["updated_at"] = "2026-05-26T11:00:00+00:00"
                return r
        raise ValueError(f"segment {segment_id} not updated")

    def delete(self, segment_id: str) -> None:
        self.rows = [r for r in self.rows if r["id"] != segment_id]

    def list_for_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        return [r for r in self.rows if r["tenant_id"] == tenant_id]


class CustomersQueryRecorder:
    """Stub for `customers.find_by_criteria`. Captures the kwargs each call
    received so tests can assert the day-to-datetime translation."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.next_response: tuple[list[dict[str, Any]], int] = ([], 0)

    def find_by_criteria(self, **kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        self.calls.append(kwargs)
        return self.next_response


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> FakeSegmentsDB:
    fake = FakeSegmentsDB()
    monkeypatch.setattr(segment_service.segments, "create", fake.create)
    monkeypatch.setattr(segment_service.segments, "get_by_id", fake.get_by_id)
    monkeypatch.setattr(segment_service.segments, "update", fake.update)
    monkeypatch.setattr(segment_service.segments, "delete", fake.delete)
    monkeypatch.setattr(
        segment_service.segments, "list_for_tenant", fake.list_for_tenant
    )
    return fake


@pytest.fixture
def customers_q(monkeypatch: pytest.MonkeyPatch) -> CustomersQueryRecorder:
    rec = CustomersQueryRecorder()
    monkeypatch.setattr(
        segment_service.customers, "find_by_criteria", rec.find_by_criteria
    )
    return rec


# ---------------------------------------------------------------------------
# CRUD — happy paths and tenant isolation
# ---------------------------------------------------------------------------


def test_create_segment_persists_criteria_as_dict(db: FakeSegmentsDB) -> None:
    row = create_segment(
        tenant_id="t-1",
        name="Loyal regulars",
        criteria=SegmentCriteria(visits_min=5, has_email=True),
    )
    assert row["tenant_id"] == "t-1"
    assert row["name"] == "Loyal regulars"
    # exclude_none keeps the payload terse — only set fields land in JSONB.
    assert row["criteria"] == {"visits_min": 5, "has_email": True}


def test_create_segment_rejects_too_short_name(db: FakeSegmentsDB) -> None:
    with pytest.raises(InvalidSegmentError):
        create_segment(
            tenant_id="t-1", name="x", criteria=SegmentCriteria()
        )


def test_create_segment_trims_name(db: FakeSegmentsDB) -> None:
    row = create_segment(
        tenant_id="t-1", name="  Padded name  ", criteria=SegmentCriteria()
    )
    assert row["name"] == "Padded name"


def test_get_owned_rejects_cross_tenant_lookup(db: FakeSegmentsDB) -> None:
    """Owner of t-1 must not be able to read t-2's segment, even if they
    know the id. 404 (not 403) so the response doesn't leak existence."""
    create_segment(tenant_id="t-1", name="Mine", criteria=SegmentCriteria())
    create_segment(tenant_id="t-2", name="Theirs", criteria=SegmentCriteria())
    # The t-2 row has id seg-2.
    with pytest.raises(NotFoundError):
        segment_service.get_owned("t-1", "seg-2")


def test_update_segment_only_name(db: FakeSegmentsDB) -> None:
    row = create_segment(
        tenant_id="t-1",
        name="Original",
        criteria=SegmentCriteria(visits_min=3),
    )
    updated = update_segment(
        tenant_id="t-1", segment_id=row["id"], name="Renamed"
    )
    assert updated["name"] == "Renamed"
    assert updated["criteria"] == {"visits_min": 3}  # untouched


def test_update_segment_only_criteria(db: FakeSegmentsDB) -> None:
    row = create_segment(
        tenant_id="t-1", name="Same", criteria=SegmentCriteria(visits_min=3)
    )
    updated = update_segment(
        tenant_id="t-1",
        segment_id=row["id"],
        criteria=SegmentCriteria(stamps_min=5),
    )
    assert updated["name"] == "Same"
    assert updated["criteria"] == {"stamps_min": 5}


def test_update_segment_no_op_returns_current(db: FakeSegmentsDB) -> None:
    row = create_segment(
        tenant_id="t-1", name="Same", criteria=SegmentCriteria(visits_min=3)
    )
    result = update_segment(tenant_id="t-1", segment_id=row["id"])
    assert result["id"] == row["id"]
    assert result["name"] == "Same"


def test_update_segment_rejects_cross_tenant(db: FakeSegmentsDB) -> None:
    create_segment(tenant_id="t-2", name="Theirs", criteria=SegmentCriteria())
    with pytest.raises(NotFoundError):
        update_segment(tenant_id="t-1", segment_id="seg-1", name="Hijack")


def test_delete_segment_removes_row(db: FakeSegmentsDB) -> None:
    create_segment(tenant_id="t-1", name="To go", criteria=SegmentCriteria())
    delete_segment(tenant_id="t-1", segment_id="seg-1")
    assert db.list_for_tenant("t-1") == []


def test_delete_segment_rejects_cross_tenant(db: FakeSegmentsDB) -> None:
    create_segment(tenant_id="t-2", name="Theirs", criteria=SegmentCriteria())
    with pytest.raises(NotFoundError):
        delete_segment(tenant_id="t-1", segment_id="seg-1")
    # And the row is still there — the rejection happened before any delete.
    assert len(db.list_for_tenant("t-2")) == 1


# ---------------------------------------------------------------------------
# Criteria schema validation
# ---------------------------------------------------------------------------


def test_criteria_rejects_inverted_visits_range() -> None:
    with pytest.raises(ValueError):
        SegmentCriteria(visits_min=10, visits_max=5)


def test_criteria_rejects_inverted_stamps_range() -> None:
    with pytest.raises(ValueError):
        SegmentCriteria(stamps_min=8, stamps_max=2)


def test_criteria_rejects_gdpr_consent_false() -> None:
    """gdpr_consent_only=false would mean targeting non-consenters; the
    schema rejects it so a future UI bug can't ship that intent."""
    with pytest.raises(ValueError):
        SegmentCriteria(gdpr_consent_only=False)


def test_criteria_accepts_all_none_as_match_everything() -> None:
    # Sanity check: an empty criteria block is valid and means "everyone".
    c = SegmentCriteria()
    assert c.visits_min is None
    assert c.has_email is None


# ---------------------------------------------------------------------------
# Evaluation — translation of day counts to datetime cutoffs
# ---------------------------------------------------------------------------


def test_evaluate_translates_last_visit_after_days(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """last_visit_after_days=30 against now=2026-05-26 → cutoff=2026-04-26."""
    row = create_segment(
        tenant_id="t-1",
        name="Active",
        criteria=SegmentCriteria(last_visit_after_days=30),
    )
    fixed_now = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)
    evaluate(tenant_id="t-1", segment_id=row["id"], now=fixed_now)

    call = customers_q.calls[0]
    assert call["last_visit_after"] == fixed_now - timedelta(days=30)
    assert call["last_visit_before"] is None
    assert call["created_after"] is None


def test_evaluate_translates_last_visit_before_days(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    row = create_segment(
        tenant_id="t-1",
        name="Dormant",
        criteria=SegmentCriteria(last_visit_before_days=60),
    )
    fixed_now = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)
    evaluate(tenant_id="t-1", segment_id=row["id"], now=fixed_now)

    call = customers_q.calls[0]
    assert call["last_visit_before"] == fixed_now - timedelta(days=60)
    assert call["last_visit_after"] is None


def test_evaluate_translates_created_after_days(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """The cohort filter the user asked for in S4-W4."""
    row = create_segment(
        tenant_id="t-1",
        name="New this week",
        criteria=SegmentCriteria(created_after_days=7),
    )
    fixed_now = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)
    evaluate(tenant_id="t-1", segment_id=row["id"], now=fixed_now)

    call = customers_q.calls[0]
    assert call["created_after"] == fixed_now - timedelta(days=7)


def test_evaluate_passes_through_count_and_channel_filters(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """No translation needed for these — they should reach the DB call
    untouched. Combo of all 6 non-time filters at once."""
    row = create_segment(
        tenant_id="t-1",
        name="Combo",
        criteria=SegmentCriteria(
            visits_min=2,
            visits_max=10,
            stamps_min=1,
            stamps_max=8,
            has_email=True,
            has_phone=False,
            gdpr_consent_only=True,
        ),
    )
    evaluate(tenant_id="t-1", segment_id=row["id"])

    call = customers_q.calls[0]
    assert call["visits_min"] == 2
    assert call["visits_max"] == 10
    assert call["stamps_min"] == 1
    assert call["stamps_max"] == 8
    assert call["has_email"] is True
    assert call["has_phone"] is False
    assert call["gdpr_consent_only"] is True


def test_evaluate_caps_limit_to_max_preview(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """Caller asking for a million rows should get the cap, not crash the
    backend. Caller asking for 0 should still get at least 1 (the engine
    clamps to [1, MAX_PREVIEW_LIMIT])."""
    row = create_segment(
        tenant_id="t-1", name="Anyone", criteria=SegmentCriteria()
    )
    evaluate(tenant_id="t-1", segment_id=row["id"], limit=1_000_000)
    assert customers_q.calls[0]["limit"] == segment_service.MAX_PREVIEW_LIMIT

    evaluate(tenant_id="t-1", segment_id=row["id"], limit=0)
    assert customers_q.calls[1]["limit"] == 1


def test_evaluate_returns_total_count_and_rows(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    row = create_segment(
        tenant_id="t-1", name="Anyone", criteria=SegmentCriteria()
    )
    customers_q.next_response = (
        [{"id": "c-1", "name": "Alice"}, {"id": "c-2", "name": "Bob"}],
        47,
    )
    total, rows, evaluated_at = evaluate(
        tenant_id="t-1",
        segment_id=row["id"],
        now=datetime(2026, 5, 26, 12, 0, tzinfo=UTC),
    )
    assert total == 47
    assert [r["id"] for r in rows] == ["c-1", "c-2"]
    assert evaluated_at == datetime(2026, 5, 26, 12, 0, tzinfo=UTC)


def test_evaluate_rejects_cross_tenant_segment(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    create_segment(tenant_id="t-2", name="Theirs", criteria=SegmentCriteria())
    with pytest.raises(NotFoundError):
        evaluate(tenant_id="t-1", segment_id="seg-1")


def test_evaluate_unsaved_does_not_persist(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """The preview-from-form endpoint must NOT create a row — that would
    leave junk segments behind every time a merchant clicked Preview."""
    evaluate_unsaved(
        tenant_id="t-1",
        criteria=SegmentCriteria(visits_min=3),
    )
    assert db.list_for_tenant("t-1") == []
    # And the query still ran.
    assert customers_q.calls[0]["visits_min"] == 3


# ---------------------------------------------------------------------------
# Drift tolerance — persisted criteria with unknown keys
# ---------------------------------------------------------------------------


def test_evaluate_ignores_unknown_keys_in_stored_criteria(
    db: FakeSegmentsDB, customers_q: CustomersQueryRecorder
) -> None:
    """If we ever add a criterion in the future and a tenant has a row from
    a newer release, the older release must still evaluate the *known* parts
    instead of crashing on Pydantic validation."""
    # Hand-roll a row with a bogus key alongside a valid one.
    db.rows.append(
        {
            "id": "seg-x",
            "tenant_id": "t-1",
            "name": "Future",
            "criteria": {"visits_min": 5, "future_unknown": "value"},
            "created_at": "2026-05-26T10:00:00+00:00",
            "updated_at": "2026-05-26T10:00:00+00:00",
        }
    )
    evaluate(tenant_id="t-1", segment_id="seg-x")
    call = customers_q.calls[0]
    assert call["visits_min"] == 5


# ---------------------------------------------------------------------------
# list_for_tenant_with_counts — member counts for the Intelligence cards (Fase E)
# ---------------------------------------------------------------------------


def test_list_for_tenant_with_counts_attaches_each_segments_size(
    db: FakeSegmentsDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each segment in the list gets its own match total, in list order, so a
    card's 'X customers' always reflects that segment's criteria."""
    create_segment(
        tenant_id="t-1", name="Regulars", criteria=SegmentCriteria(visits_min=5)
    )
    create_segment(
        tenant_id="t-1", name="New", criteria=SegmentCriteria(created_after_days=7)
    )

    totals = iter([12, 3])
    monkeypatch.setattr(
        segment_service.customers,
        "find_by_criteria",
        lambda **_: ([], next(totals)),
    )

    pairs = list_for_tenant_with_counts("t-1")

    assert [row["name"] for row, _ in pairs] == ["Regulars", "New"]
    assert [count for _, count in pairs] == [12, 3]


def test_list_for_tenant_with_counts_empty_when_no_segments(
    db: FakeSegmentsDB,
) -> None:
    assert list_for_tenant_with_counts("t-1") == []
