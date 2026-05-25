from dataclasses import dataclass
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.config import Settings, get_settings
from app.db import tenant_members

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        log.info("jwt_decode_failed", error=str(exc))
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Token missing sub")
    email = payload.get("email")
    return CurrentUser(user_id=sub, email=email if isinstance(email, str) else None)


def get_current_tenant_id(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> str:
    rows = tenant_members.list_for_user(user.user_id)
    if not rows:
        raise HTTPException(
            status_code=403,
            detail="No tenant for this user. POST /v1/me/bootstrap first.",
        )
    first = rows[0]
    tenant_id = first["tenant_id"]
    if not isinstance(tenant_id, str):
        raise HTTPException(status_code=500, detail="Malformed tenant_member")
    return tenant_id
