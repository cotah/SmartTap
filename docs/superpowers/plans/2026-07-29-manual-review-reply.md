# Manual Review Reply Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the cancelled Places API bridge with a manual paste-a-review → AI reply generator on `/dashboard/reviews`, feeding a few-shot loop from previously approved replies.

**Architecture:** No new external APIs. A form on `/dashboard/reviews` posts the pasted review to a new backend endpoint that calls Claude (existing `anthropic_client.generate_text`) with tenant context (name, business_type, opening_hours, menu_info, brand_voice from migration 016) + few-shot examples of previously approved replies (rating-proximity prioritised). On "Copy", the review + final reply are saved to the existing `reviews` table with `source='manual'`, `status='approved'` — becoming a few-shot example for next time. The GBP pipeline (cron + publish) stays untouched and remains the primary path once quota is approved; its drafts also benefit from the enriched system prompt. `tenants.enabled_modules` ships as planned and gates dashboard nav links.

**Context empirically confirmed (2026-07-29):** Places API (New) returns max 5 reviews sorted by relevance (Panda test: newest was 3 months stale, all 5★). Bridge cancelled entirely — no watermark, no gap banner. `GOOGLE_PLACES_API_KEY` is out of scope (Henrique may delete it from `backend/.env` and Google Cloud).

**Accepted trade-off:** a manually pasted review has `google_review_id = NULL`, so if the GBP cron later fetches the same review it will create a second row (draft `pending`). Low volume, owner just dismisses it. No dedupe heuristic in v1 (YAGNI).

**Tech Stack:** FastAPI + Supabase (backend), Anthropic SDK via existing `anthropic_client`, Next.js 15 App Router + server actions (web), pytest with monkeypatch stubs (repo test pattern — service layer only, DB stubbed).

**Commands (run from repo root unless noted):**
- Backend tests: `cd backend && uv run pytest tests/ -q`
- Backend lint: `cd backend && uv run ruff check . && uv run mypy app`
- Web typecheck/lint: `pnpm --filter web typecheck && pnpm --filter web lint` (fallback: `pnpm turbo typecheck lint`)

---

## File Structure

- Create: `backend/migrations/018_manual_reviews.sql` — `reviews.source`, nullable `google_review_id`, partial unique index, `tenants.enabled_modules`
- Modify: `backend/app/db/reviews.py` — `create()` gains `source` / optional `google_review_id`; new `list_reply_examples()`
- Modify: `backend/app/services/review_response_service.py` — enriched `_reply_system_prompt`, new `generate_manual_reply()` + `save_manual_review()`
- Create: `backend/tests/test_manual_review_reply.py`
- Modify: `backend/app/schemas/review.py` — `ManualGenerateIn/Out`, `ManualReviewCreateIn`; `ReviewOut.google_review_id` nullable + `source`
- Modify: `backend/app/routers/reviews.py` — `POST /reviews/generate`, `POST /reviews/manual`
- Modify: `backend/app/schemas/me.py` + `backend/app/routers/me.py` + `backend/app/routers/onboarding.py` — `enabled_modules`
- Modify: `packages/api/src/client.ts` — types + `generateReviewReply` / `createManualReview` methods
- Create: `apps/web/src/app/dashboard/reviews/manual-reply-card.tsx`
- Modify: `apps/web/src/app/dashboard/reviews/actions.ts`, `page.tsx`
- Modify: `apps/web/src/app/dashboard/layout.tsx`, `shell.tsx`, `side-nav.tsx` — module gating

---

### Task 1: Migration 018

**Files:**
- Create: `backend/migrations/018_manual_reviews.sql`

- [ ] **Step 1: Write the migration**

```sql
-- SmartTap: manual review replies (Places API bridge cancelled 2026-07-29)
-- Apply AFTER 017_instagram_page_picker.sql
--
-- Manual path: owner pastes a Google review into /dashboard/reviews, Claude
-- drafts a reply, owner copies it and pastes it on Google themselves. Those
-- rows have no google_review_id, hence source + nullable column + partial
-- unique index (dedupe still enforced for cron-fetched rows).

ALTER TABLE reviews
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'google'
        CHECK (source IN ('google', 'manual'));

ALTER TABLE reviews ALTER COLUMN google_review_id DROP NOT NULL;

-- Replace the table constraint with a partial unique index: manual rows
-- (google_review_id IS NULL) don't participate in dedupe.
ALTER TABLE reviews DROP CONSTRAINT reviews_tenant_id_google_review_id_key;
CREATE UNIQUE INDEX idx_reviews_tenant_gid
    ON reviews(tenant_id, google_review_id)
    WHERE google_review_id IS NOT NULL;

-- status gains 'approved': owner approved/copied a reply that is NOT published
-- via the Google API (manual copy-paste). Kept as TEXT (no CHECK), consistent
-- with 009: pending | published | dismissed | failed | approved.

-- Per-tenant module toggles (decision 2026-07-29). Default = both on, so
-- existing tenants see no change.
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS enabled_modules TEXT[] NOT NULL DEFAULT '{loyalty,reviews}';
```

- [ ] **Step 2: Commit**

```bash
git add backend/migrations/018_manual_reviews.sql
git commit -m "feat: migration 018 — manual review source + enabled_modules"
```

> Prod apply happens at the end (Task 9) via Supabase SQL editor / MCP, before deploy.

---

### Task 2: DB layer

**Files:**
- Modify: `backend/app/db/reviews.py`

Repo pattern: the DB layer is thin Supabase CRUD, covered indirectly by service tests that stub it — no direct DB tests.

- [ ] **Step 1: Make `create()` accept source + optional google_review_id**

In `backend/app/db/reviews.py`, change the `create` signature (keep everything else):

```python
def create(
    *,
    tenant_id: str,
    google_review_id: str | None,
    author: str | None,
    rating: int | None,
    comment: str | None,
    created_at_google: str | None,
    ai_draft: str | None,
    status: Status = "pending",
    source: str = "google",
) -> Row:
    client = get_supabase_admin()
    payload: Row = {
        "tenant_id": tenant_id,
        "google_review_id": google_review_id,
        "author": author,
        "rating": rating,
        "comment": comment,
        "created_at_google": created_at_google,
        "ai_draft": ai_draft,
        "status": status,
        "source": source,
    }
    res = client.table("reviews").insert(payload).execute()
    rows = cast(list[Row], res.data or [])
    if not rows:
        raise ValueError("review not created")
    return rows[0]
```

Also update the module docstring's status line comment to `pending | published | dismissed | failed | approved`.

- [ ] **Step 2: Add `list_reply_examples()`**

Append to `backend/app/db/reviews.py`:

```python
def list_reply_examples(tenant_id: str, *, limit: int = 50) -> list[Row]:
    """Approved/published replies used as few-shot examples for new drafts.
    Newest-first; the service re-ranks by rating proximity to the review
    being answered."""
    client = get_supabase_admin()
    res = (
        client.table("reviews")
        .select("rating, comment, reply_text")
        .eq("tenant_id", tenant_id)
        .in_("status", ["approved", "published"])
        .not_.is_("reply_text", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return cast(list[Row], res.data or [])
```

- [ ] **Step 3: Run existing tests to confirm nothing broke**

Run: `cd backend && uv run pytest tests/test_review_response_service.py -q`
Expected: PASS (the cron passes `google_review_id` as keyword already).

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/reviews.py
git commit -m "feat: reviews db — manual source + few-shot example query"
```

---

### Task 3: Service — enriched prompt + manual generate/save (TDD)

**Files:**
- Modify: `backend/app/services/review_response_service.py`
- Create: `backend/tests/test_manual_review_reply.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_manual_review_reply.py`:

```python
"""Tests for the manual review-reply path (Places bridge replacement).

The owner pastes a review into the dashboard; Claude drafts a reply using
tenant context + few-shot examples of previously approved replies. On copy,
the review is stored as source='manual', status='approved'.
"""

from typing import Any

import pytest

from app.errors import BusinessError
from app.services import review_response_service as svc

TENANT = "t-1"


@pytest.fixture
def stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {
        "tenant": {
            "id": TENANT,
            "name": "ACME Barbers",
            "business_type": "barbershop",
            "opening_hours": "Mon-Sat 9-18",
            "menu_info": "Cuts, fades, beard trims",
            "brand_voice": "Friendly and casual",
        },
        "examples": [],
        "anthropic_ok": True,
        "captured": {},
        "created": [],
    }

    monkeypatch.setattr(svc.tenants, "get_by_id", lambda tid: state["tenant"])
    monkeypatch.setattr(
        svc.reviews, "list_reply_examples", lambda tid, **kw: state["examples"]
    )
    monkeypatch.setattr(
        svc.anthropic_client, "is_configured", lambda: state["anthropic_ok"]
    )

    def fake_generate(**kw: Any) -> str:
        state["captured"] = kw
        return "DRAFT REPLY"

    monkeypatch.setattr(svc.anthropic_client, "generate_text", fake_generate)

    def fake_create(**kw: Any) -> dict[str, Any]:
        state["created"].append(kw)
        return {"id": "r-manual", **kw}

    monkeypatch.setattr(svc.reviews, "create", fake_create)
    return state


# ---------------------------------------------------------------------------
# generate_manual_reply
# ---------------------------------------------------------------------------


def test_generate_returns_draft_and_uses_tenant_context(stubs: dict[str, Any]) -> None:
    draft = svc.generate_manual_reply(
        TENANT, comment="Great cut!", rating=5, author="Alex"
    )
    assert draft == "DRAFT REPLY"
    system = stubs["captured"]["system"]
    assert "ACME Barbers" in system
    assert "Mon-Sat 9-18" in system
    assert "Cuts, fades, beard trims" in system
    assert "Friendly and casual" in system
    assert "Alex left a 5-star review" in stubs["captured"]["user_text"]


def test_generate_omits_missing_context_lines(stubs: dict[str, Any]) -> None:
    stubs["tenant"] = {"id": TENANT, "name": "ACME", "business_type": "cafe"}
    svc.generate_manual_reply(TENANT, comment="ok", rating=3, author=None)
    system = stubs["captured"]["system"]
    assert "Opening hours" not in system
    assert "Brand voice" not in system


def test_generate_few_shot_prioritises_similar_rating(stubs: dict[str, Any]) -> None:
    stubs["examples"] = [
        {"rating": 5, "comment": "five", "reply_text": "REPLY-FIVE"},
        {"rating": 1, "comment": "one", "reply_text": "REPLY-ONE"},
        {"rating": 2, "comment": "two", "reply_text": "REPLY-TWO"},
    ]
    svc.generate_manual_reply(TENANT, comment="bad", rating=1, author=None)
    system = stubs["captured"]["system"]
    # 1★ target: the 1★ and 2★ examples must rank before the 5★ one.
    assert system.index("REPLY-ONE") < system.index("REPLY-FIVE")
    assert system.index("REPLY-TWO") < system.index("REPLY-FIVE")


def test_generate_caps_examples_at_four(stubs: dict[str, Any]) -> None:
    stubs["examples"] = [
        {"rating": 4, "comment": f"c{i}", "reply_text": f"REPLY-{i}"} for i in range(6)
    ]
    svc.generate_manual_reply(TENANT, comment="nice", rating=4, author=None)
    system = stubs["captured"]["system"]
    assert sum(1 for i in range(6) if f"REPLY-{i}" in system) == 4


def test_generate_no_examples_no_example_block(stubs: dict[str, Any]) -> None:
    svc.generate_manual_reply(TENANT, comment="hi", rating=4, author=None)
    assert "approved before" not in stubs["captured"]["system"]


def test_generate_unconfigured_raises_business_error(stubs: dict[str, Any]) -> None:
    stubs["anthropic_ok"] = False
    with pytest.raises(BusinessError):
        svc.generate_manual_reply(TENANT, comment="hi", rating=5, author=None)


# ---------------------------------------------------------------------------
# save_manual_review
# ---------------------------------------------------------------------------


def test_save_stores_manual_approved(stubs: dict[str, Any]) -> None:
    row = svc.save_manual_review(
        TENANT,
        comment="Great cut!",
        rating=5,
        author="Alex",
        ai_draft="DRAFT REPLY",
        reply_text="Thanks Alex! See you soon.",
    )
    assert row["id"] == "r-manual"
    created = stubs["created"][0]
    assert created["source"] == "manual"
    assert created["status"] == "approved"
    assert created["google_review_id"] is None
    assert created["reply_text"] == "Thanks Alex! See you soon."


def test_cron_prompt_still_has_tenant_context(stubs: dict[str, Any]) -> None:
    # The GBP cron path shares the enriched system prompt (free improvement).
    draft = svc.generate_draft(
        stubs["tenant"], {"rating": 5, "author": "Sam", "comment": "great"}
    )
    assert draft == "DRAFT REPLY"
    assert "Mon-Sat 9-18" in stubs["captured"]["system"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_manual_review_reply.py -q`
Expected: FAIL — `AttributeError: ... has no attribute 'generate_manual_reply'` (and `list_reply_examples` monkeypatch works since Task 2 added it).

- [ ] **Step 3: Implement in `review_response_service.py`**

Replace `_reply_system_prompt` and add the new functions (below the existing `_review_user_text`; `generate_draft` keeps working — it calls `_reply_system_prompt(tenant)` with no examples):

```python
FEW_SHOT_LIMIT = 4


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
        )
    return "\n\n".join(parts)


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
    post on Google themselves). Feeds the few-shot loop."""
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
    return reviews.update(row["id"], {"reply_text": reply_text})
```

Note: `save_manual_review` sets `reply_text` via `update` because `create` doesn't take it (kept minimal — one extra call, no signature churn). Also add `test_save_stores_manual_approved`'s expectation: assert on the create kwargs (as written above) and stub `reviews.update` in the fixture:

```python
    def fake_update(rid: str, fields: dict[str, Any]) -> dict[str, Any]:
        state["created"][-1].update(fields)
        return {"id": rid, **state["created"][-1]}

    monkeypatch.setattr(svc.reviews, "update", fake_update)
```

(Add this to the fixture in Step 1 — it's part of the test file.)

- [ ] **Step 4: Run the new tests + full backend suite**

Run: `cd backend && uv run pytest tests/test_manual_review_reply.py tests/test_review_response_service.py -q` then `uv run pytest tests/ -q`
Expected: PASS.

- [ ] **Step 5: Lint + typecheck, then commit**

Run: `cd backend && uv run ruff check . && uv run mypy app`

```bash
git add backend/app/services/review_response_service.py backend/tests/test_manual_review_reply.py
git commit -m "feat: manual review reply — tenant-context prompt + few-shot + save"
```

---

### Task 4: Schemas + router endpoints

**Files:**
- Modify: `backend/app/schemas/review.py`
- Modify: `backend/app/routers/reviews.py`

- [ ] **Step 1: Extend schemas**

In `backend/app/schemas/review.py` — make `ReviewOut.google_review_id` nullable, add `source`, and append the manual models:

```python
class ReviewOut(BaseModel):
    id: str
    google_review_id: str | None
    author: str | None
    rating: int | None
    comment: str | None
    created_at_google: str | None
    ai_draft: str | None
    reply_text: str | None
    status: str
    published_at: str | None
    created_at: str
    source: str = "google"
```

```python
class ManualGenerateIn(BaseModel):
    """A review the owner pasted in, to draft a reply for."""

    comment: str = Field(min_length=1, max_length=4000)
    rating: int = Field(ge=1, le=5)
    author: str | None = Field(default=None, max_length=200)


class ManualGenerateOut(BaseModel):
    draft: str


class ManualReviewCreateIn(BaseModel):
    """Approved manual reply — stored when the owner copies it."""

    comment: str = Field(min_length=1, max_length=4000)
    rating: int = Field(ge=1, le=5)
    author: str | None = Field(default=None, max_length=200)
    ai_draft: str | None = Field(default=None, max_length=4000)
    reply_text: str = Field(min_length=1, max_length=4000)
```

- [ ] **Step 2: Add endpoints**

In `backend/app/routers/reviews.py` — import the new schemas, add `source` to `_to_out` (`source=row.get("source") or "google"`), and append:

```python
@router.post("/reviews/generate", response_model=ManualGenerateOut)
def generate_manual_reply(
    body: ManualGenerateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> ManualGenerateOut:
    """Draft a reply for a pasted review (manual fallback while the Google
    Business API quota is pending). Nothing is stored at this stage."""
    draft = review_response_service.generate_manual_reply(
        tenant_id, comment=body.comment, rating=body.rating, author=body.author
    )
    return ManualGenerateOut(draft=draft)


@router.post("/reviews/manual", response_model=ReviewOut)
def create_manual_review(
    body: ManualReviewCreateIn,
    tenant_id: Annotated[str, Depends(require_active_tenant)],
) -> ReviewOut:
    """Store the pasted review + approved reply (owner copied it to Google).
    Feeds the few-shot examples for future drafts."""
    row = review_response_service.save_manual_review(
        tenant_id,
        comment=body.comment,
        rating=body.rating,
        author=body.author,
        ai_draft=body.ai_draft,
        reply_text=body.reply_text,
    )
    return _to_out(row)
```

- [ ] **Step 3: Full backend check + commit**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check . && uv run mypy app`
Expected: PASS.

```bash
git add backend/app/schemas/review.py backend/app/routers/reviews.py
git commit -m "feat: manual review generate + save endpoints"
```

---

### Task 5: `enabled_modules` in TenantSummary

**Files:**
- Modify: `backend/app/schemas/me.py:8-19`
- Modify: `backend/app/routers/me.py:14-25`
- Modify: `backend/app/routers/onboarding.py:31-40`

- [ ] **Step 1: Add the field to the schema**

In `backend/app/schemas/me.py`, add to `TenantSummary`:

```python
    # Per-tenant module toggles (migration 018). Defaults keep old rows working.
    enabled_modules: list[str] = ["loyalty", "reviews"]
```

- [ ] **Step 2: Populate it at both construction sites**

In `backend/app/routers/me.py` `_summary(...)` and `backend/app/routers/onboarding.py`'s `TenantSummary(...)`, add:

```python
        enabled_modules=tenant.get("enabled_modules") or ["loyalty", "reviews"],
```

- [ ] **Step 3: Backend check + commit**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check . && uv run mypy app`

```bash
git add backend/app/schemas/me.py backend/app/routers/me.py backend/app/routers/onboarding.py
git commit -m "feat: expose tenants.enabled_modules in TenantSummary"
```

---

### Task 6: API client (packages/api)

**Files:**
- Modify: `packages/api/src/client.ts`

- [ ] **Step 1: Types**

At `packages/api/src/client.ts:419-433`:

```ts
export type ReviewStatus =
  | "pending"
  | "published"
  | "dismissed"
  | "failed"
  | "approved";
```

In `interface Review`: change `google_review_id: string;` → `google_review_id: string | null;` and add `source: "google" | "manual";`.

In `interface TenantSummary` (line ~174) add: `enabled_modules: string[];`

New input/output types next to `Review`:

```ts
export interface ManualGenerateInput {
  comment: string;
  rating: number;
  author?: string | null;
}

export interface ManualReviewCreateInput extends ManualGenerateInput {
  ai_draft?: string | null;
  reply_text: string;
}
```

- [ ] **Step 2: Methods**

In the `ApiClient` interface (after `dismissReview`, line ~518):

```ts
  generateReviewReply: (body: ManualGenerateInput) => Promise<{ draft: string }>;
  createManualReview: (body: ManualReviewCreateInput) => Promise<Review>;
```

In the implementation object (after the `dismissReview` implementation, ~line 776), matching the file's existing style:

```ts
    generateReviewReply: (body) =>
      request<{ draft: string }>(`/v1/reviews/generate`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    createManualReview: (body) =>
      request<Review>(`/v1/reviews/manual`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
```

- [ ] **Step 3: Typecheck + commit**

Run: `pnpm turbo typecheck` (or `pnpm --filter @smarttap/api typecheck && pnpm --filter web typecheck`)
Expected: PASS.

```bash
git add packages/api/src/client.ts
git commit -m "feat: api client — manual review generate/save + enabled_modules"
```

---

### Task 7: Manual reply card (web)

**Files:**
- Create: `apps/web/src/app/dashboard/reviews/manual-reply-card.tsx`
- Modify: `apps/web/src/app/dashboard/reviews/actions.ts`
- Modify: `apps/web/src/app/dashboard/reviews/page.tsx`

- [ ] **Step 1: Server actions**

Append to `apps/web/src/app/dashboard/reviews/actions.ts`:

```ts
export type GenerateReplyResult =
  | { ok: true; draft: string }
  | { ok: false; message: string };

/** Draft a reply for a review the owner pasted in (manual fallback). */
export async function generateManualReplyAction(input: {
  comment: string;
  rating: number;
  author?: string | null;
}): Promise<GenerateReplyResult> {
  const comment = (input.comment ?? "").trim();
  if (comment.length === 0) {
    return { ok: false, message: "Paste the review text first." };
  }
  try {
    const api = getAuthApiClient();
    const { draft } = await api.generateReviewReply({
      comment,
      rating: input.rating,
      author: input.author?.trim() || null,
    });
    return { ok: true, draft };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not generate a reply." };
    }
    return { ok: false, message: "Could not generate a reply. Try again." };
  }
}

/** Store the pasted review + approved reply once the owner copies it. */
export async function approveManualReplyAction(input: {
  comment: string;
  rating: number;
  author?: string | null;
  aiDraft?: string | null;
  replyText: string;
}): Promise<ReviewActionResult> {
  const replyText = (input.replyText ?? "").trim();
  if (replyText.length === 0) {
    return { ok: false, message: "Reply can't be empty." };
  }
  try {
    const api = getAuthApiClient();
    const review = await api.createManualReview({
      comment: input.comment.trim(),
      rating: input.rating,
      author: input.author?.trim() || null,
      ai_draft: input.aiDraft ?? null,
      reply_text: replyText,
    });
    revalidatePath("/dashboard/reviews");
    return { ok: true, review };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save the reply." };
    }
    return { ok: false, message: "Could not save the reply. Try again." };
  }
}
```

- [ ] **Step 2: The card component**

Create `apps/web/src/app/dashboard/reviews/manual-reply-card.tsx` (Dark Electric tokens, same visual grammar as `reviews-client.tsx`):

```tsx
"use client";

import { useState, useTransition } from "react";

import {
  approveManualReplyAction,
  generateManualReplyAction,
} from "./actions";

/**
 * Manual fallback while the Google Business API quota is pending: the owner
 * pastes a review, Claude drafts a reply, the owner edits + copies it and
 * pastes it on Google themselves. Copying also saves the pair as an approved
 * example, so future drafts match the owner's tone (few-shot loop).
 */
export function ManualReplyCard() {
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(5);
  const [author, setAuthor] = useState("");
  const [draft, setDraft] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [pending, startTransition] = useTransition();

  function handleGenerate() {
    setError(null);
    setCopied(false);
    startTransition(async () => {
      const res = await generateManualReplyAction({
        comment,
        rating,
        author: author || null,
      });
      if (res.ok) {
        setDraft(res.draft);
        setReply(res.draft);
      } else {
        setError(res.message);
      }
    });
  }

  function handleCopy() {
    setError(null);
    startTransition(async () => {
      try {
        await navigator.clipboard.writeText(reply.trim());
      } catch {
        setError("Could not access the clipboard — copy the text manually.");
        return;
      }
      const res = await approveManualReplyAction({
        comment,
        rating,
        author: author || null,
        aiDraft: draft,
        replyText: reply,
      });
      if (res.ok) {
        setCopied(true);
      } else {
        // Clipboard already has the text; surface the save failure.
        setError(res.message);
      }
    });
  }

  function handleReset() {
    setComment("");
    setRating(5);
    setAuthor("");
    setDraft(null);
    setReply("");
    setError(null);
    setCopied(false);
  }

  return (
    <div className="rounded-2xl border border-electric-border bg-electric-surface p-4">
      <p className="font-display text-lg">Reply to a review</p>
      <p className="text-sm text-electric-text-muted">
        Paste a Google review, get a suggested reply, copy it and post it on
        Google. Copied replies teach SmartTap your tone.
      </p>

      <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
        Review text
      </label>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={3}
        maxLength={4000}
        className="mt-1 w-full rounded-xl border border-electric-border p-3 text-sm focus:border-electric-cyan focus:outline-none"
        placeholder="Paste the customer's review here…"
      />

      <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
        <div>
          <span className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Rating
          </span>
          <div className="mt-1 flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                role="radio"
                aria-checked={rating === star}
                aria-label={`${star} star${star > 1 ? "s" : ""}`}
                onClick={() => setRating(star)}
                className={`text-2xl leading-none transition-colors ${
                  star <= rating
                    ? "text-electric-cyan"
                    : "text-electric-text-muted"
                }`}
              >
                ★
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Reviewer name (optional)
          </label>
          <input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            maxLength={200}
            className="mt-1 w-full rounded-xl border border-electric-border p-2.5 text-sm focus:border-electric-cyan focus:outline-none"
            placeholder="e.g. Alex"
          />
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={pending || comment.trim().length === 0}
          className="shrink-0 rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
        >
          {pending && draft === null ? "Generating…" : "Generate reply"}
        </button>
      </div>

      {draft !== null ? (
        <div className="mt-4">
          <label className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Suggested reply (edit before copying)
          </label>
          <textarea
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            rows={4}
            maxLength={4000}
            className="mt-1 w-full rounded-xl border border-electric-border p-3 text-sm focus:border-electric-cyan focus:outline-none"
          />
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              disabled={pending || reply.trim().length === 0}
              className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg disabled:opacity-60"
            >
              {copied ? "Copied ✓" : pending ? "Working…" : "Copy reply"}
            </button>
            {copied ? (
              <button
                type="button"
                onClick={handleReset}
                className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold text-electric-text-muted"
              >
                Reply to another
              </button>
            ) : null}
          </div>
          {copied ? (
            <p className="mt-2 text-sm text-electric-text-muted">
              Paste it as your reply on Google. Saved as an approved example.
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
```

- [ ] **Step 3: Add the card to the page**

In `apps/web/src/app/dashboard/reviews/page.tsx`, import and render it above `ReviewsClient` (it must work with or without a Google connection):

```tsx
import { ManualReplyCard } from "./manual-reply-card";
```

```tsx
      <ReviewSummary stats={stats} />

      <ManualReplyCard />

      <ReviewsClient reviews={items} googleStatus={googleStatus} />
```

- [ ] **Step 4: Typecheck + lint + commit**

Run: `pnpm --filter web typecheck && pnpm --filter web lint`
Expected: PASS.

```bash
git add apps/web/src/app/dashboard/reviews/
git commit -m "feat: manual review reply card on /dashboard/reviews"
```

---

### Task 8: Nav gating by enabled_modules

**Files:**
- Modify: `apps/web/src/app/dashboard/side-nav.tsx:26-36` and its props
- Modify: `apps/web/src/app/dashboard/shell.tsx`
- Modify: `apps/web/src/app/dashboard/layout.tsx`

- [ ] **Step 1: Map links to modules and filter in SideNav**

In `side-nav.tsx`, add an optional `module` to `NavLink` entries and filter:

```tsx
const NAV_LINKS: NavLink[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/customers", label: "Customers", icon: Users },
  { href: "/dashboard/segments", label: "Segments", icon: Layers, module: "loyalty" },
  { href: "/dashboard/tags", label: "NFC tags", icon: Tag },
  { href: "/dashboard/reward", label: "Reward", icon: Gift, module: "loyalty" },
  { href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone, module: "loyalty" },
  { href: "/dashboard/reviews", label: "Reviews", icon: Star, module: "reviews" },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
];
```

Add `module?: "loyalty" | "reviews";` to the `NavLink` interface, `enabledModules: string[];` to `Props`, and change the render loop:

```tsx
        {NAV_LINKS.filter(
          (link) => !link.module || enabledModules.includes(link.module),
        ).map((link) => {
```

(Destructure `enabledModules` in the component signature alongside `mobileOpen`/`onClose`.)

- [ ] **Step 2: Thread the prop through shell + layout**

`shell.tsx`: add `enabledModules: string[];` to `Props`, destructure it, pass `enabledModules={enabledModules}` to `<SideNav … />`.

`layout.tsx`: pass `enabledModules={ctx.tenant.enabled_modules ?? ["loyalty", "reviews"]}` to `<DashboardShell … >`.

- [ ] **Step 3: Typecheck + lint + commit**

Run: `pnpm --filter web typecheck && pnpm --filter web lint`
Expected: PASS. (Default `{loyalty,reviews}` → zero visible change for existing tenants.)

```bash
git add apps/web/src/app/dashboard/side-nav.tsx apps/web/src/app/dashboard/shell.tsx apps/web/src/app/dashboard/layout.tsx
git commit -m "feat: gate dashboard nav links by tenants.enabled_modules"
```

---

### Task 9: Final verification + prod rollout

- [ ] **Step 1: Full local gate**

Run: `cd backend && uv run pytest tests/ -q && uv run ruff check . && uv run mypy app`
Run (repo root): `pnpm turbo typecheck lint`
Expected: all PASS.

- [ ] **Step 2: Apply migration 018 to prod Supabase** (`qmemsvkeiygdwxyzadrc`) via SQL editor or Supabase MCP `apply_migration` — BEFORE pushing (backend insert sends `source`, which needs the column).

- [ ] **Step 3: Push to main** (deploys Vercel + Railway automatically):

```bash
git push origin main
```

- [ ] **Step 4: Smoke check on prod** — open `/dashboard/reviews`, paste a real review text, generate, copy; confirm the card works and no console/Sentry errors. (Requires `ANTHROPIC_API_KEY` on Railway — already set for Sprint 5.)

- [ ] **Step 5: Housekeeping** — Henrique may remove `GOOGLE_PLACES_API_KEY` from `backend/.env` and delete the key in Google Cloud Console (no code references it).
