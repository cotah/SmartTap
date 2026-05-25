from fastapi import APIRouter, Request

from app.schemas.tap import (
    CustomerSnapshot,
    RewardAvailable,
    RewardStateSnapshot,
    TapEventIn,
    TapResponse,
    TenantPublic,
)
from app.services.stamp_engine import compute_reward_state
from app.services.tap_service import TapContext, process_tap

router = APIRouter(tags=["taps"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else None


@router.post("/taps/{tag_uuid}", response_model=TapResponse)
def register_tap(tag_uuid: str, body: TapEventIn, request: Request) -> TapResponse:
    ctx = TapContext(
        tag_uuid=tag_uuid,
        device_type=body.device_type,
        interaction_type=body.interaction_type,
        magic_link_token=body.magic_link_token,
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
    )

    result = process_tap(ctx)

    state = compute_reward_state(result.stamps_current, result.tenant["stamps_for_reward"])

    return TapResponse(
        tenant=TenantPublic(
            id=result.tenant["id"],
            slug=result.tenant["slug"],
            name=result.tenant["name"],
            logo_url=result.tenant["logo_url"],
            primary_color=result.tenant["primary_color"],
            accent_color=result.tenant["accent_color"],
            reward_description=result.tenant["reward_description"],
            google_review_url=result.tenant["google_review_url"],
        ),
        customer=(
            CustomerSnapshot(
                id=result.customer["id"],
                name=result.customer["name"],
                current_stamps=result.customer["current_stamps"],
            )
            if result.customer is not None
            else None
        ),
        tap_id=result.tap_id,
        stamp_awarded=result.stamp_awarded,
        stamps_current=result.stamps_current,
        reward_state=RewardStateSnapshot(
            current_stamps=state.current_stamps,
            stamps_for_reward=state.stamps_for_reward,
            stamps_remaining=state.stamps_remaining,
            reward_ready=state.reward_ready,
            progress_percent=state.progress_percent,
        ),
        reward_available=(
            RewardAvailable(
                id=result.reward_available["id"],
                validation_code=result.reward_available["validation_code"],
                description=result.reward_available["description"],
                expires_at=result.reward_available["expires_at"],
            )
            if result.reward_available is not None
            else None
        ),
    )
