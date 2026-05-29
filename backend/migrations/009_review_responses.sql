-- SmartTap S5 Feature 3 (Phase A): Google review responses
-- Apply AFTER 008_whatsapp_bot.sql

-- Per-tenant Google Business Profile OAuth connection. One row per tenant
-- (UNIQUE). refresh_token is sensitive — accessed only via the service-role
-- key (RLS on). Encrypting at rest (pgcrypto) is recommended before connecting
-- real accounts; tracked as a follow-up.
CREATE TABLE tenant_google_connections (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    account_id    TEXT,
    location_id   TEXT,
    connected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_tgc_updated BEFORE UPDATE ON tenant_google_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Reviews fetched from Google + their AI draft and approval state.
-- google_review_id dedupes so the cron only generates a draft once per review.
CREATE TABLE reviews (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    google_review_id  TEXT NOT NULL,
    author            TEXT,
    rating            INT,
    comment           TEXT,
    created_at_google TIMESTAMPTZ,
    ai_draft          TEXT,
    reply_text        TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
                      -- pending | published | dismissed | failed
    published_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, google_review_id)
);

-- Dashboard lists pending reviews newest-first; cron checks existence by
-- (tenant, google_review_id) which the UNIQUE constraint already indexes.
CREATE INDEX idx_reviews_tenant_status
    ON reviews(tenant_id, status, created_at_google DESC);

CREATE TRIGGER trg_reviews_updated BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS — backend uses the service-role key (bypasses), policies kept on for
-- defence in depth like every other table.
ALTER TABLE tenant_google_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
