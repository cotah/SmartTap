from pydantic import BaseModel


class TenantSummary(BaseModel):
    id: str
    slug: str
    name: str
    business_type: str
    plan: str
    is_active: bool
    trial_ends_at: str | None = None
    onboarding_complete: bool


class MeResponse(BaseModel):
    user_id: str
    email: str | None
    tenant: TenantSummary | None


class BootstrapIn(BaseModel):
    business_name: str | None = None


class BootstrapResponse(BaseModel):
    tenant: TenantSummary
    is_new: bool
