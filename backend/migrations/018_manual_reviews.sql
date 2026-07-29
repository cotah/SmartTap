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
