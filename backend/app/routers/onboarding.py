from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_tenant_id
from app.schemas.me import TenantSummary
from app.schemas.onboarding import OnboardingCompleteIn
from app.services import onboarding_service
from app.services.onboarding_service import OnboardingPayload

router = APIRouter(tags=["onboarding"])


@router.post("/onboarding/complete", response_model=TenantSummary)
def complete_onboarding_endpoint(
    body: OnboardingCompleteIn,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> TenantSummary:
    tenant = onboarding_service.complete_onboarding(
        tenant_id,
        OnboardingPayload(
            business_name=body.business_name,
            business_type=body.business_type,
            google_review_url=body.google_review_url,
            stamps_for_reward=body.stamps_for_reward,
            reward_description=body.reward_description,
            reward_expires_days=body.reward_expires_days,
            stamp_rate_limit_minutes=body.stamp_rate_limit_minutes,
        ),
    )
    return TenantSummary(
        id=tenant["id"],
        slug=tenant["slug"],
        name=tenant["name"],
        business_type=tenant["business_type"],
        plan=tenant["plan"],
        is_active=tenant["is_active"],
        trial_ends_at=tenant.get("trial_ends_at"),
        onboarding_complete=bool(tenant.get("reward_description")),
    )
