from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class CustomerIdentifyIn(BaseModel):
    tenant_id: str
    phone: str = Field(pattern=r"^\+353[1-9]\d{6,9}$")
    name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    birthday: date | None = None
    gdpr_consent: bool
    gdpr_consent_text: str = Field(min_length=10, max_length=2000)


class CustomerIdentifyOut(BaseModel):
    customer_id: str
    magic_link_token: str
    stamps_current: int = Field(ge=0)


class CustomerListItem(BaseModel):
    id: str
    name: str | None
    phone: str | None
    current_stamps: int = Field(ge=0)
    total_visits: int = Field(ge=0)
    last_visit_at: datetime | None
    created_at: datetime
    has_reward_ready: bool


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    limit: int = Field(ge=1)


class CustomerStats(BaseModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    at_risk: int = Field(ge=0)
    reward_ready: int = Field(ge=0)
