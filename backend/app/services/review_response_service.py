"""Review-response service (S5 Feature 3, Phase A).

Two entry points:
    - run_daily(): the cron. For each connected tenant, pull new Google reviews,
      draft a reply with Claude, and store it as `pending` for the owner to
      approve in the dashboard. Idempotent via the (tenant, google_review_id)
      dedupe.
    - publish_review(): called by the dashboard "Publish" endpoint. Posts the
      owner-approved reply to Google and flips the review to `published`.

Nothing is published without human approval (v1 decision). Without Google API
credentials, list/publish no-op, so the cron runs clean and the dashboard works
against test data — build-to-activate.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.db import google_connections, reviews, tenants
from app.errors import BusinessError, NotFoundError
from app.services import anthropic_client, google_client

log = structlog.get_logger(__name__)

# Cap per-tenant drafting per run so one location with a big review backlog
# can't monopolise the cron; the next run picks up the rest.
PER_TENANT_LIMIT = 50


@dataclass
class ReviewResponseRunResult:
    tenants_scanned: int
    reviews_drafted: int
    errors: list[str] = field(default_factory=list)


FEW_SHOT_LIMIT = 4

# Data minimisation: stored few-shot examples never keep the reviewer's name.
NAME_PLACEHOLDER = "[CUSTOMER NAME]"


def _anonymize_reply(reply_text: str, author: str | None) -> str:
    """Replace the review author's name in a reply with NAME_PLACEHOLDER.

    Matches the full name and each name part (whole words only, case-
    insensitive). Single-letter parts (initials) are skipped so "J Murphy"
    doesn't blank out every standalone letter."""
    if not author:
        return reply_text
    full = author.strip()
    parts = [p for p in full.split() if len(p) > 1]
    candidates = [full, *parts] if len(full) > 1 else parts
    if not candidates:
        return reply_text
    # Longest first so "John Smith" wins over "John".
    alternatives = sorted({c.lower() for c in candidates}, key=len, reverse=True)
    pattern = r"\b(?:" + "|".join(re.escape(c) for c in alternatives) + r")\b"
    return re.sub(pattern, NAME_PLACEHOLDER, reply_text, flags=re.IGNORECASE)


def _reply_system_prompt(
    tenant: dict[str, Any], examples: list[dict[str, Any]] | None = None
) -> str:
    name = (tenant.get("name") or "the business").strip()
    btype = (tenant.get("business_type") or "local business").strip()
    parts = [
        f"You write public replies to Google reviews on behalf of {name}, a "
        f"{btype} in Ireland, as the owner. Write ONLY the reply text — no "
        "preamble, no quotes. Keep it short (1-3 sentences), warm and genuine, "
        "in the same language as the review. Thank the reviewer by first name if "
        "present. For positive reviews, be appreciative and specific. For "
        "negative reviews, be empathetic and invite them to resolve it offline "
        "(e.g. contact the shop) WITHOUT admitting fault, blaming staff, or "
        "disclosing private details. Never invent facts or promotions."
    ]
    context_lines = [
        f"{label}: {value.strip()}"
        for label, value in (
            ("Opening hours", tenant.get("opening_hours")),
            ("Menu / services", tenant.get("menu_info")),
            ("Brand voice", tenant.get("brand_voice")),
        )
        if isinstance(value, str) and value.strip()
    ]
    if context_lines:
        parts.append("Business context:\n" + "\n".join(context_lines))
    if examples:
        blocks = [
            f"Review ({ex.get('rating')}★): {(ex.get('comment') or '').strip()}\n"
            f"Reply: {(ex.get('reply_text') or '').strip()}"
            for ex in examples
        ]
        parts.append(
            "Replies the owner approved before — match their tone and style:\n\n"
            + "\n\n".join(blocks)
            + f"\n\nIn these examples {NAME_PLACEHOLDER} is a privacy placeholder "
            "for the reviewer's name. Never write it literally — use the actual "
            "reviewer's first name if you know it, otherwise no name."
        )
    return "\n\n".join(parts)


def _review_user_text(review: dict[str, Any]) -> str:
    rating = review.get("rating")
    author = review.get("author") or "A customer"
    comment = (review.get("comment") or "").strip() or "(no written comment)"
    return f"{author} left a {rating}-star review:\n\n{comment}"


def generate_draft(tenant: dict[str, Any], review: dict[str, Any]) -> str | None:
    """Draft a reply with Claude. Returns None when Anthropic isn't configured
    (the review is still stored pending so the owner can write one manually)."""
    if not anthropic_client.is_configured():
        return None
    return anthropic_client.generate_text(
        system=_reply_system_prompt(tenant),
        user_text=_review_user_text(review),
    )


def _pick_examples(
    examples: list[dict[str, Any]], rating: int, limit: int = FEW_SHOT_LIMIT
) -> list[dict[str, Any]]:
    """Closest-rating first; ties keep the incoming (newest-first) order."""
    return sorted(examples, key=lambda ex: abs((ex.get("rating") or 3) - rating))[:limit]


def generate_manual_reply(
    tenant_id: str, *, comment: str, rating: int, author: str | None
) -> str:
    """Draft a reply for a review the owner pasted into the dashboard.
    Raises BusinessError when Anthropic isn't configured — unlike the cron,
    there's nothing useful to store without a draft."""
    if not anthropic_client.is_configured():
        raise BusinessError("AI reply generation is not configured")
    tenant = tenants.get_by_id(tenant_id) or {"id": tenant_id}
    examples = _pick_examples(reviews.list_reply_examples(tenant_id), rating)
    return anthropic_client.generate_text(
        system=_reply_system_prompt(tenant, examples),
        user_text=_review_user_text(
            {"rating": rating, "author": author, "comment": comment}
        ),
    )


def save_manual_review(
    tenant_id: str,
    *,
    comment: str,
    rating: int,
    author: str | None,
    ai_draft: str | None,
    reply_text: str,
) -> dict[str, Any]:
    """Persist a pasted review + its approved reply (the owner copied it to
    post on Google themselves). Feeds the few-shot loop.

    The reply is anonymised before storage (data minimisation): the author's
    name becomes NAME_PLACEHOLDER so stored examples carry no customer names."""
    row = reviews.create(
        tenant_id=tenant_id,
        google_review_id=None,
        author=author,
        rating=rating,
        comment=comment,
        created_at_google=None,
        ai_draft=ai_draft,
        status="approved",
        source="manual",
    )
    return reviews.update(
        row["id"], {"reply_text": _anonymize_reply(reply_text, author)}
    )


def _process_tenant(connection: dict[str, Any]) -> tuple[int, list[str]]:
    tenant_id = connection["tenant_id"]
    tenant = tenants.get_by_id(tenant_id) or {"id": tenant_id}
    drafted = 0
    errors: list[str] = []

    fetched = google_client.list_new_reviews(connection)
    for raw in fetched[:PER_TENANT_LIMIT]:
        gid = raw.get("google_review_id")
        if not isinstance(gid, str):
            continue
        if reviews.exists(tenant_id, gid):
            continue  # dedupe — already drafted
        try:
            draft = generate_draft(tenant, raw)
            reviews.create(
                tenant_id=tenant_id,
                google_review_id=gid,
                author=raw.get("author"),
                rating=raw.get("rating"),
                comment=raw.get("comment"),
                created_at_google=raw.get("created_at_google"),
                ai_draft=draft,
                status="pending",
            )
            drafted += 1
        except Exception as exc:
            log.exception("review_draft_failed", tenant_id=tenant_id, error=str(exc))
            errors.append(f"review {gid}: {exc!s}")

    return drafted, errors


def run_daily(*, now: datetime | None = None) -> ReviewResponseRunResult:
    """Cron entry point. `now` accepted for symmetry with the other crons."""
    connections = google_connections.list_connected()
    log.info("review_response_run_start", tenants=len(connections))

    total_drafted = 0
    all_errors: list[str] = []
    for connection in connections:
        drafted, errors = _process_tenant(connection)
        total_drafted += drafted
        all_errors.extend(errors)

    log.info(
        "review_response_run_complete",
        tenants_scanned=len(connections),
        reviews_drafted=total_drafted,
    )
    return ReviewResponseRunResult(
        tenants_scanned=len(connections),
        reviews_drafted=total_drafted,
        errors=all_errors,
    )


def publish_review(
    *, tenant_id: str, review_id: str, now: datetime | None = None
) -> dict[str, Any]:
    """Publish the owner-approved reply to Google (dashboard action).

    Uses reply_text if the owner edited one, else the AI draft. Raises
    NotFoundError if the review isn't this tenant's, BusinessError if there's no
    text to publish or the publish didn't succeed (e.g. API not live yet) — in
    which case the review is marked `failed` so the owner sees it needs a retry.
    """
    current = now or datetime.now(UTC)
    review = reviews.get_owned(tenant_id, review_id)
    if review is None:
        raise NotFoundError("Review not found")

    text = (review.get("reply_text") or review.get("ai_draft") or "").strip()
    if not text:
        raise BusinessError("No reply text to publish")

    connection = google_connections.get_by_tenant(tenant_id)
    if connection is None:
        raise BusinessError("Google account not connected")

    gid = str(review["google_review_id"])
    try:
        ok = google_client.publish_reply(connection, gid, text)
    except Exception as exc:
        log.exception("review_publish_failed", tenant_id=tenant_id, error=str(exc))
        reviews.update(review_id, {"status": "failed"})
        raise BusinessError("Failed to publish reply to Google") from exc

    if not ok:
        # Not configured / incomplete connection — keep it actionable.
        reviews.update(review_id, {"status": "failed", "reply_text": text})
        raise BusinessError(
            "Google API not available yet — reply saved but not published"
        )

    return reviews.mark_published(review_id, text, current)
