"""Pydantic models for customer segments (S4-W4).

The criteria object is the heart of the feature — every field is optional,
None means "criterion not applied", and the engine combines all set fields
with AND. Adding a new criterion later is a 1-field addition here plus a
1-branch addition in `customers.find_by_criteria`.

Naming convention for time-based criteria: `..._after_days` means "the
event is within the last N days", `..._before_days` means "the event is
older than N days". Days are integer counts; the engine grounds them in
the request's `now` (UTC).
"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SegmentCriteria(BaseModel):
    """All fields optional. Engine ANDs every set field. Unset = ignore."""

    # Visit counts — total lifetime visits.
    visits_min: int | None = Field(default=None, ge=0, le=1_000_000)
    visits_max: int | None = Field(default=None, ge=0, le=1_000_000)

    # Stamps — current balance (resets on reward redemption).
    stamps_min: int | None = Field(default=None, ge=0, le=10_000)
    stamps_max: int | None = Field(default=None, ge=0, le=10_000)

    # Recency. last_visit_after_days = "visited in the last N days"
    # (i.e. recent). last_visit_before_days = "no visit in N+ days"
    # (i.e. dormant). Setting both at once is allowed and means
    # "neither too recent nor too old".
    last_visit_after_days: int | None = Field(default=None, ge=1, le=3650)
    last_visit_before_days: int | None = Field(default=None, ge=1, le=3650)

    # Cohort filter — signups within the last N days. Useful for "new
    # customers from this week" mailings.
    created_after_days: int | None = Field(default=None, ge=1, le=3650)

    # Contact-channel filters. None = ignore; True = must have; False =
    # must NOT have. Marketers commonly want "has email AND GDPR consent"
    # which is `has_email=True, gdpr_consent_only=True`.
    has_email: bool | None = None
    has_phone: bool | None = None

    # GDPR gate. Only useful as True (we never want to mass-message customers
    # who haven't consented). Set to None to ignore; False is rejected since
    # there's no defensible business reason to target *non-consenters*.
    gdpr_consent_only: bool | None = None

    @model_validator(mode="after")
    def _validate_ranges(self) -> "SegmentCriteria":
        if (
            self.visits_min is not None
            and self.visits_max is not None
            and self.visits_min > self.visits_max
        ):
            raise ValueError("visits_min cannot exceed visits_max")
        if (
            self.stamps_min is not None
            and self.stamps_max is not None
            and self.stamps_min > self.stamps_max
        ):
            raise ValueError("stamps_min cannot exceed stamps_max")
        if self.gdpr_consent_only is False:
            raise ValueError(
                "gdpr_consent_only=false is not allowed; "
                "leave unset to skip the filter"
            )
        return self


class SegmentCreateIn(BaseModel):
    """Payload for `POST /v1/segments`."""

    name: str = Field(min_length=2, max_length=80)
    criteria: SegmentCriteria = Field(default_factory=SegmentCriteria)


class SegmentUpdateIn(BaseModel):
    """Patch a segment. Both fields optional — only sent fields change.
    Setting criteria to an empty object resets all filters."""

    name: str | None = Field(default=None, min_length=2, max_length=80)
    criteria: SegmentCriteria | None = None


class SegmentOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    criteria: SegmentCriteria
    created_at: str
    updated_at: str
    # Current number of customers matching the segment. Populated only by the
    # list endpoint (the Intelligence cards); None on create/update/get, which
    # don't evaluate the criteria.
    member_count: int | None = None


class SegmentListResponse(BaseModel):
    items: list[SegmentOut]


class SegmentCustomerPreview(BaseModel):
    """Single row in the preview payload. Mirrors the dashboard customers
    list columns so the UI can reuse its existing rendering."""

    id: str
    name: str | None
    phone: str | None
    email: str | None
    current_stamps: int
    total_visits: int
    last_visit_at: str | None
    created_at: str


class SegmentPreviewResponse(BaseModel):
    """Response from `GET /v1/segments/{id}/preview`.

    `total` is the full count matching the criteria (after filters, before
    limit). `items` is the truncated list the dashboard renders. Returning
    both means the merchant sees "13 customers match (showing first 5)"
    without a second roundtrip.
    """

    total: int
    items: list[SegmentCustomerPreview]
    evaluated_at: datetime
