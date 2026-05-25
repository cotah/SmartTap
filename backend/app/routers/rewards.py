from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_current_tenant_id, get_current_user
from app.schemas.reward import ValidateRewardIn, ValidateRewardOut
from app.services.reward_service import validate_and_redeem, validate_and_redeem_by_code

router = APIRouter(tags=["rewards"])


@router.post("/rewards/validate", response_model=ValidateRewardOut)
def validate_reward_by_code(
    body: ValidateRewardIn,
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ValidateRewardOut:
    result = validate_and_redeem_by_code(
        tenant_id=tenant_id,
        validation_code=body.validation_code,
        redeemed_by_user=user.user_id,
    )
    return ValidateRewardOut(
        reward_id=result.reward_id,
        redeemed_at=result.redeemed_at,
        description=result.description,
        customer_id=result.customer_id,
        customer_name=result.customer_name,
    )


@router.post("/rewards/{reward_id}/validate", response_model=ValidateRewardOut)
def validate_reward(reward_id: str, body: ValidateRewardIn) -> ValidateRewardOut:
    # Legacy endpoint kept for the customer-facing /t/[uuid] redeem flow.
    # Not auth-gated: the customer proves possession by knowing the 6-digit code.
    result = validate_and_redeem(
        reward_id=reward_id,
        validation_code=body.validation_code,
        redeemed_by_user=None,
    )
    return ValidateRewardOut(
        reward_id=result.reward_id,
        redeemed_at=result.redeemed_at,
        description=result.description,
        customer_id=result.customer_id,
        customer_name=result.customer_name,
    )
