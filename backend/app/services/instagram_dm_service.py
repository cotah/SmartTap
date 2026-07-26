"""Instagram DM assistant — auto-reply service.

Flow (called by the /webhooks/instagram router for each inbound event):
    1. Look up the tenant by the IG business account id in the payload
       (meta_conn_get_by_ig) — unknown accounts are logged and skipped.
    2. Build a per-tenant context prompt (name, business_type, opening_hours,
       menu_info, brand_voice) — zero hardcoded business facts.
    3. Draft a short reply with Claude (same one-shot style as the review
       responder) and send it via the Page's messaging endpoint.
    4. Log the interaction (answered/failed) for the monthly report.

Never raises: the webhook must always 200 (Meta retries on 5xx → duplicate
replies). Every failure path degrades to a log line + a `failed` row.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from app.db import instagram_interactions, meta_connections, tenants
from app.services import anthropic_client, meta_client

log = structlog.get_logger(__name__)

# A DM reply should be chat-sized, not essay-sized.
MAX_REPLY_TOKENS = 512


@dataclass(frozen=True)
class InstagramEvent:
    """One inbound message/mention, as extracted by the webhook router."""

    ig_account_id: str  # entry[].id — identifies the tenant
    sender_id: str  # IGSID of the Instagram user who wrote to us
    text: str | None  # message text (None for a bare story mention)
    is_story_mention: bool


def _system_prompt(tenant: dict[str, Any], *, is_story_mention: bool) -> str:
    name = (tenant.get("name") or "the business").strip()
    btype = (tenant.get("business_type") or "local business").strip()
    parts = [
        f"You answer Instagram direct messages on behalf of {name}, a {btype} "
        "in Ireland, as a friendly member of the team. Write ONLY the reply "
        "text — no preamble, no quotes, no sign-off. Keep it short (1-3 "
        "sentences), warm and helpful, in the same language as the customer's "
        "message. Never invent facts, prices, promotions or availability — if "
        "you don't know, say the team will get back to them."
    ]
    if is_story_mention:
        parts.append(
            "The customer just mentioned the business in their Instagram "
            "story — start by thanking them for the mention."
        )
    opening_hours = (tenant.get("opening_hours") or "").strip()
    if opening_hours:
        parts.append(f"Opening hours: {opening_hours}")
    menu_info = (tenant.get("menu_info") or "").strip()
    if menu_info:
        parts.append(f"Menu / services info: {menu_info}")
    brand_voice = (tenant.get("brand_voice") or "").strip()
    if brand_voice:
        parts.append(f"Brand voice guidance: {brand_voice}")
    return "\n\n".join(parts)


def _user_text(event: InstagramEvent) -> str:
    if event.is_story_mention:
        if event.text:
            return (
                "The customer mentioned us in their story and wrote:\n\n"
                f"{event.text}"
            )
        return "The customer mentioned us in their Instagram story (no text)."
    return event.text or ""


def handle_event(event: InstagramEvent) -> None:
    """Process one inbound Instagram event end-to-end. Never raises."""
    conn = meta_connections.get_by_ig_account(event.ig_account_id)
    if conn is None:
        # Not one of our tenants (or enc key missing) — nothing to do.
        log.warning("instagram_unknown_account", ig_account_id=event.ig_account_id)
        return

    tenant_id = str(conn["tenant_id"])
    interaction_type = "story_mention" if event.is_story_mention else "dm"

    if not event.text and not event.is_story_mention:
        # Non-text DM (image, audio…) — out of scope for v1, don't log noise.
        log.info("instagram_skip_non_text", tenant_id=tenant_id)
        return

    tenant = tenants.get_by_id(tenant_id) or {"id": tenant_id}

    reply: str | None = None
    status = "failed"
    try:
        if anthropic_client.is_configured():
            reply = anthropic_client.generate_text(
                system=_system_prompt(tenant, is_story_mention=event.is_story_mention),
                user_text=_user_text(event),
                max_tokens=MAX_REPLY_TOKENS,
            )
        else:
            log.info("instagram_skip_reply", reason="anthropic_not_configured")

        if reply:
            sent = meta_client.send_dm(
                ig_business_account_id=str(conn["instagram_business_account_id"]),
                page_access_token=str(conn["page_access_token"]),
                recipient_id=event.sender_id,
                text=reply,
            )
            status = "answered" if sent else "failed"
    except Exception as exc:
        log.exception("instagram_reply_failed", tenant_id=tenant_id, error=str(exc))
        status = "failed"

    try:
        instagram_interactions.create(
            tenant_id=tenant_id,
            interaction_type=interaction_type,
            external_sender_id=event.sender_id,
            incoming_text=event.text,
            reply_text=reply,
            status=status,
        )
    except Exception as exc:
        # Logging must never take the webhook down either.
        log.exception("instagram_log_failed", tenant_id=tenant_id, error=str(exc))
