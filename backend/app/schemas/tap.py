from typing import Literal

from pydantic import BaseModel, Field


class TapEventIn(BaseModel):
    magic_link_token: str | None = None
    device_type: Literal["ios", "android", "other", "unknown"] = "unknown"
    interaction_type: Literal["nfc", "qr"] = "nfc"


class TenantPublic(BaseModel):
    id: str
    slug: str
    name: str
    logo_url: str | None = None
    primary_color: str
    accent_color: str


class CustomerSnapshot(BaseModel):
    id: str
    name: str | None = None
    current_stamps: int = Field(ge=0)


class RewardAvailable(BaseModel):
    id: str
    validation_code: str
    description: str


class TapResponse(BaseModel):
    tenant: TenantPublic
    customer: CustomerSnapshot | None = None
    stamps_current: int = Field(ge=0)
    reward_available: RewardAvailable | None = None
