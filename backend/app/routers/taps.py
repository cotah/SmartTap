from fastapi import APIRouter, HTTPException

from app.schemas.tap import TapEventIn, TapResponse

router = APIRouter(tags=["taps"])


@router.post("/taps/{tag_uuid}", response_model=TapResponse)
def register_tap(tag_uuid: str, body: TapEventIn) -> TapResponse:
    _ = body
    raise HTTPException(status_code=501, detail=f"Not implemented yet (tag={tag_uuid})")
