from datetime import date

from pydantic import BaseModel, Field


class CustomerIdentifyIn(BaseModel):
    tenant_id: str
    phone: str = Field(pattern=r"^\+353[1-9]\d{6,9}$")
    name: str | None = Field(default=None, min_length=1, max_length=80)
    birthday: date | None = None
    gdpr_consent: bool
    gdpr_consent_text: str = Field(min_length=10, max_length=2000)


class CustomerIdentifyOut(BaseModel):
    customer_id: str
    magic_link_token: str
    stamps_current: int = Field(ge=0)
