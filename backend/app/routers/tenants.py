from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["tenants"])


@router.get("/public/tenants/{slug}")
def get_public_tenant(slug: str) -> dict[str, str]:
    _ = slug
    raise HTTPException(status_code=501, detail="Not implemented yet")
