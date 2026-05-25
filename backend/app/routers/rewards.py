from fastapi import APIRouter

from app.schemas.reward import ValidateRewardIn, ValidateRewardOut
from app.services.reward_service import validate_and_redeem

router = APIRouter(tags=["rewards"])


@router.post("/rewards/{reward_id}/validate", response_model=ValidateRewardOut)
def validate_reward(reward_id: str, body: ValidateRewardIn) -> ValidateRewardOut:
    # TODO: gate behind dashboard auth in Sprint 2 (pass current_user_id as redeemed_by_user)
    result = validate_and_redeem(
        reward_id=reward_id,
        validation_code=body.validation_code,
        redeemed_by_user=None,
    )
    return ValidateRewardOut(
        reward_id=result.reward_id,
        redeemed_at=result.redeemed_at,
        description=result.description,
    )
