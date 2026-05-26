from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CampaignType = Literal["double_stamp", "reactivation", "birthday", "custom"]
CampaignStatus = Literal["draft", "active", "paused", "ended"]


class CampaignCreateIn(BaseModel):
    """Payload for `POST /v1/campaigns`. Only double_stamp is implemented in
    S4-W1; other types are accepted by the DB but not exposed yet."""

    name: str = Field(min_length=2, max_length=80)
    type: Literal["double_stamp"] = "double_stamp"
    multiplier: int = Field(ge=2, le=5)
    starts_at: datetime
    ends_at: datetime
    # Default to draft so the owner can review before going live. Setting
    # active here triggers the "one active per tenant" uniqueness check.
    status: Literal["draft", "active"] = "draft"


class CampaignUpdateIn(BaseModel):
    """Patch a draft campaign's fields. All optional — only sent fields change.
    Status transitions go through the dedicated endpoint to keep the state
    machine surface obvious."""

    name: str | None = Field(default=None, min_length=2, max_length=80)
    multiplier: int | None = Field(default=None, ge=2, le=5)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class CampaignStatusUpdateIn(BaseModel):
    status: Literal["draft", "active", "paused", "ended"]


class CampaignOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: CampaignType
    status: CampaignStatus
    multiplier: int = Field(ge=1, le=5)
    starts_at: str | None
    ends_at: str | None
    created_at: str


class CampaignListResponse(BaseModel):
    items: list[CampaignOut]
