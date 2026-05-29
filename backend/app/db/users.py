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


def get_user_id_by_email(email: str) -> str | None:
    """Reverse lookup: email -> Supabase auth user id, or None.

    Used by the WhatsApp bot's OTP flow to map the email the owner types to a
    tenant. GoTrue's admin API has no direct get-by-email, so we page through
    list_users and match case-insensitively. Fine for our scale (target ~200
    tenants); revisit with a server-side filter if the user base grows large.

    Never raises — a miss (or any error) collapses to None so the caller can
    keep the response anti-enumeration (same reply whether or not it matched).
    """
    target = email.strip().lower()
    if not target:
        return None
    try:
        client = get_supabase_admin()
        page = 1
        # Hard cap so a huge user base can't turn this into a runaway scan:
        # 50 pages x 50/page = 2500 users before we give up.
        while page <= 50:
            resp = client.auth.admin.list_users(page=page, per_page=50)
            users = resp if isinstance(resp, list) else getattr(resp, "users", []) or []
            if not users:
                return None
            for user in users:
                user_email = getattr(user, "email", None)
                if isinstance(user_email, str) and user_email.lower() == target:
                    uid = getattr(user, "id", None)
                    return str(uid) if uid else None
            if len(users) < 50:
                return None
            page += 1
    except Exception as exc:
        log.warning("auth_user_email_lookup_failed", error=str(exc))
        return None
    return None
