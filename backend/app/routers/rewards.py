from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["rewards"])


class ValidateRewardIn(BaseModel):
    validation_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/rewards/{reward_id}/validate")
def validate_reward(reward_id: str, body: ValidateRewardIn) -> dict[str, str]:
    _ = body
    raise HTTPException(status_code=501, detail=f"Not implemented yet (id={reward_id})")
