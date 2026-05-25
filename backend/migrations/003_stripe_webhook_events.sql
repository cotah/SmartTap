-- SmartTap S3-W3: Stripe webhook idempotency store
-- Apply AFTER 002_rls_policies.sql

-- One row per Stripe event we've handled. event_id is the natural PK
-- (Stripe's evt_xxx); a duplicate INSERT means we've seen it before and
-- the handler must short-circuit (idempotency).
CREATE TABLE stripe_webhook_events (
    event_id        TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_message   TEXT
);

CREATE INDEX idx_stripe_webhook_events_type ON stripe_webhook_events(type);
CREATE INDEX idx_stripe_webhook_events_processed_at ON stripe_webhook_events(processed_at DESC);

-- No application code should ever read or write this table through the
-- anon/authenticated keys. Enabling RLS without policies denies all access
-- to those roles; the backend uses service_role which bypasses RLS.
ALTER TABLE stripe_webhook_events ENABLE ROW LEVEL SECURITY;
