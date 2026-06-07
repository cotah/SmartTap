"""Business rules for customer segments (S4-W4).

Two responsibilities:

    1. CRUD orchestration — create/read/update/delete segments with tenant
       isolation. Mirrors campaign_service patterns.
    2. Evaluation engine — translate a SegmentCriteria payload into the
       day-grounded cutoffs the DB function expects, run the query, return
       (total, preview rows).

The criteria model itself owns shape validation (Pydantic); this module
only enforces business rules that need the world (tenant ownership, "now"
for relative time windows).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.db import customers, segments
from app.errors import BusinessError, NotFoundError
from app.schemas.segment import SegmentCriteria

log = structlog.get_logger(__name__)

Row = dict[str, Any]

# Hard cap on the preview list. Anything above this is irrelevant for a
# "show me what this segment matches" UI — at 200 rows the page would
# already be unreadable. Total count is still accurate beyond this.
MAX_PREVIEW_LIMIT = 200


class InvalidSegmentError(BusinessError):
    status_code = 422
    code = "invalid_segment"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_name(name: str) -> None:
    cleaned = name.strip()
    if len(cleaned) < 2 or len(cleaned) > 80:
        raise InvalidSegmentError(
            "Segment name must be between 2 and 80 characters.",
            detail={"name_length": str(len(cleaned))},
        )


# ---------------------------------------------------------------------------
# CRUD orchestration
# ---------------------------------------------------------------------------


def list_for_tenant(tenant_id: str) -> list[Row]:
    return segments.list_for_tenant(tenant_id)


def list_for_tenant_with_counts(
    tenant_id: str, *, now: datetime | None = None
) -> list[tuple[Row, int]]:
    """List segments plus each one's current match count, in list order.

    Powers the Intelligence cards' 'X customers' badge. Runs one count query
    per segment (limit=1 — we only need the total), reusing the same criteria
    engine as the preview so the number matches what the preview would show.
    Segments are few and unpaginated, so N small counts is acceptable.
    """
    rows = segments.list_for_tenant(tenant_id)
    result: list[tuple[Row, int]] = []
    for row in rows:
        criteria = _criteria_from_row(row)
        total, _, _ = _run_query(
            tenant_id=tenant_id, criteria=criteria, limit=1, now=now
        )
        result.append((row, total))
    return result


def get_owned(tenant_id: str, segment_id: str) -> Row:
    """Fetch + assert tenant ownership. Raises NotFoundError on missing OR
    cross-tenant so external callers can't probe for segment existence."""
    row = segments.get_by_id(segment_id)
    if row is None or row.get("tenant_id") != tenant_id:
        raise NotFoundError("Segment not found", detail={"segment_id": segment_id})
    return row


def create_segment(
    *,
    tenant_id: str,
    name: str,
    criteria: SegmentCriteria,
) -> Row:
    _validate_name(name)
    row = segments.create(
        {
            "tenant_id": tenant_id,
            "name": name.strip(),
            "criteria": criteria.model_dump(exclude_none=True),
        }
    )
    log.info("segment_created", tenant_id=tenant_id, segment_id=row["id"])
    return row


def update_segment(
    *,
    tenant_id: str,
    segment_id: str,
    name: str | None = None,
    criteria: SegmentCriteria | None = None,
) -> Row:
    """Partial update. Sending only `name` leaves criteria untouched and
    vice-versa. Sending an empty SegmentCriteria explicitly clears the
    filter set (all fields None → matches every customer)."""
    # Ownership check is the side-effect we want even when there's nothing
    # to update — it gives the router a clean 404 path.
    get_owned(tenant_id, segment_id)

    fields: dict[str, Any] = {}
    if name is not None:
        _validate_name(name)
        fields["name"] = name.strip()
    if criteria is not None:
        fields["criteria"] = criteria.model_dump(exclude_none=True)

    if not fields:
        # No-op update — return the current row so the API contract stays
        # consistent (always returns the latest state).
        return get_owned(tenant_id, segment_id)

    updated = segments.update(segment_id, fields)
    log.info("segment_updated", tenant_id=tenant_id, segment_id=segment_id)
    return updated


def delete_segment(*, tenant_id: str, segment_id: str) -> None:
    """Ownership check first so we never delete cross-tenant rows even if
    the router somehow stripped the id from a stale tab."""
    get_owned(tenant_id, segment_id)
    segments.delete(segment_id)
    log.info("segment_deleted", tenant_id=tenant_id, segment_id=segment_id)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _criteria_from_row(row: Row) -> SegmentCriteria:
    """Reconstruct the validated criteria from the JSONB column. Unknown
    fields are silently dropped — schema drift between persisted and current
    must not crash the evaluator. Missing fields default to None."""
    raw = row.get("criteria") or {}
    if not isinstance(raw, dict):
        return SegmentCriteria()
    # Filter to known fields so Pydantic doesn't reject unrecognised keys
    # (which a future schema change might introduce in storage but not yet
    # in code).
    known = SegmentCriteria.model_fields.keys()
    cleaned = {k: v for k, v in raw.items() if k in known}
    return SegmentCriteria.model_validate(cleaned)


def evaluate(
    *,
    tenant_id: str,
    segment_id: str,
    limit: int = 20,
    now: datetime | None = None,
) -> tuple[int, list[Row], datetime]:
    """Run a segment's criteria against the customers table.

    Returns (total_count, preview_rows, evaluated_at). `now` is injectable
    for tests so the "X days ago" cutoffs are deterministic.
    """
    row = get_owned(tenant_id, segment_id)
    criteria = _criteria_from_row(row)
    return _run_query(tenant_id=tenant_id, criteria=criteria, limit=limit, now=now)


def evaluate_unsaved(
    *,
    tenant_id: str,
    criteria: SegmentCriteria,
    limit: int = 20,
    now: datetime | None = None,
) -> tuple[int, list[Row], datetime]:
    """Same as evaluate() but takes a criteria payload directly — used by the
    "Preview" button on the create-segment form, before persistence."""
    return _run_query(tenant_id=tenant_id, criteria=criteria, limit=limit, now=now)


def _run_query(
    *,
    tenant_id: str,
    criteria: SegmentCriteria,
    limit: int,
    now: datetime | None,
) -> tuple[int, list[Row], datetime]:
    """Shared core: translate day-counts to datetime cutoffs and call the DB."""
    capped_limit = max(1, min(limit, MAX_PREVIEW_LIMIT))
    current = now or datetime.now(UTC)

    last_visit_after = (
        current - timedelta(days=criteria.last_visit_after_days)
        if criteria.last_visit_after_days is not None
        else None
    )
    last_visit_before = (
        current - timedelta(days=criteria.last_visit_before_days)
        if criteria.last_visit_before_days is not None
        else None
    )
    created_after = (
        current - timedelta(days=criteria.created_after_days)
        if criteria.created_after_days is not None
        else None
    )

    rows, total = customers.find_by_criteria(
        tenant_id=tenant_id,
        visits_min=criteria.visits_min,
        visits_max=criteria.visits_max,
        stamps_min=criteria.stamps_min,
        stamps_max=criteria.stamps_max,
        last_visit_after=last_visit_after,
        last_visit_before=last_visit_before,
        created_after=created_after,
        has_email=criteria.has_email,
        has_phone=criteria.has_phone,
        gdpr_consent_only=criteria.gdpr_consent_only,
        limit=capped_limit,
    )
    return total, rows, current
