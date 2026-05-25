from dataclasses import dataclass
from typing import Annotated, Any

import httpx
import structlog
from fastapi import Depends, Header, HTTPException, status
from jose import jwt
from jose.exceptions import JWTError

from app.config import Settings, get_settings
from app.db import tenant_members

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None


_jwks_cache: dict[str, Any] = {}


def _jwks_url(settings: Settings) -> str:
    base = settings.supabase_url.rstrip("/")
    return f"{base}/auth/v1/.well-known/jwks.json"


def _fetch_jwks(settings: Settings) -> dict[str, Any]:
    res = httpx.get(_jwks_url(settings), timeout=5.0)
    res.raise_for_status()
    body: dict[str, Any] = res.json()
    return body


def _get_key_for_kid(
    settings: Settings, kid: str, *, allow_refresh: bool = True
) -> dict[str, Any] | None:
    jwks = _jwks_cache.get("data")
    if jwks is None:
        jwks = _fetch_jwks(settings)
        _jwks_cache["data"] = jwks

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key  # type: ignore[no-any-return]

    if allow_refresh:
        _jwks_cache.pop("data", None)
        return _get_key_for_kid(settings, kid, allow_refresh=False)
    return None


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="Supabase URL not configured")

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Malformed token") from exc

    alg = unverified_header.get("alg")
    kid = unverified_header.get("kid")

    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(status_code=500, detail="JWT secret not configured")
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        elif alg in {"ES256", "RS256", "EdDSA"}:
            if not isinstance(kid, str):
                raise HTTPException(status_code=401, detail="Token missing kid")
            key = _get_key_for_kid(settings, kid)
            if key is None:
                raise HTTPException(status_code=401, detail="Signing key not found in JWKS")
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
                audience="authenticated",
            )
        else:
            raise HTTPException(status_code=401, detail=f"Unsupported alg: {alg}")
    except JWTError as exc:
        log.info("jwt_decode_failed", error=str(exc), alg=alg)
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
