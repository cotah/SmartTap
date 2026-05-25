from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "smarttap-backend",
        "timestamp": datetime.now(UTC).isoformat(),
    }
