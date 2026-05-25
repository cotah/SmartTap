from typing import Literal

from pydantic import BaseModel

TrialStatus = Literal["active", "expiring_soon", "expired", "subscribed", "inactive"]


class TenantSummary(BaseModel):
    id: str
    slug: str
    name: str
    business_type: str
    plan: str
    is_active: bool
    trial_ends_at: str | None = None
    onboarding_complete: bool
    # Derived from plan + is_active + trial_ends_at; the frontend uses this to
    # decide between green / amber / red banners and which CTAs to surface.
    trial_status: TrialStatus = "active"


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    tenant: TenantSummary | None


class BootstrapIn(BaseModel):
    business_name: str | None = None


class BootstrapResponse(BaseModel):
    tenant: TenantSummary
    is_new: bool
