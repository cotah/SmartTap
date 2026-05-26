"""Lookups against Supabase auth.users.

We don't mirror auth data into our own tables — email lives in
auth.users.email, owned by Supabase. These helpers wrap the admin API and
return None on any failure so callers (notably the email_service) can
degrade gracefully without 5xx-ing user flows over a missing email.
"""

import structlog

from app.services.supabase_client import get_supabase_admin

log = structlog.get_logger(__name__)


def get_email_by_user_id(user_id: str) -> str | None:
    """Return the email for a Supabase auth user, or None if not found / error.

    Never raises — emails are a "nice to have" in our codebase, not a hard
    dependency. The caller logs the miss and moves on.
    """
    try:
        client = get_supabase_admin()
        resp = client.auth.admin.get_user_by_id(user_id)
    except Exception as exc:
        # Network blip, malformed UUID, deleted user, key without admin scope —
        # all collapse to "no email available". Log once so we can spot patterns.
        log.warning("auth_user_lookup_failed", user_id=user_id, error=str(exc))
        return None

    user = getattr(resp, "user", None)
    if user is None:
        return None
    email = getattr(user, "email", None)
    return str(email) if email else None
