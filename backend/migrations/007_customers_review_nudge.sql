-- SmartTap S5 Feature 2: review-nudge email tracking
-- Apply AFTER 006_customer_segments.sql

-- When the daily cron sent a "leave us a review" nudge to this customer. Used
-- to enforce a per-customer cooldown (30 days) so a customer who tapped but
-- never reviews doesn't get pestered every week. NULL means we've never
-- nudged them. Distinct from last_reactivation_sent_at — the two flows have
-- different triggers, cadences, and CTAs (see 005_customers_reactivation.sql).
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS last_review_nudge_sent_at TIMESTAMPTZ;

-- The review-nudge cron resolves candidates from recent taps, then checks
-- the cooldown on this column for that small candidate set (tenant-scoped).
-- The partial index mirrors 005: it only covers rows that can ever receive
-- an outbound email (consenting customers with an address), keeping it tiny.
CREATE INDEX IF NOT EXISTS idx_customers_tenant_review_nudge
    ON customers(tenant_id, last_review_nudge_sent_at)
    WHERE email IS NOT NULL AND gdpr_consent = TRUE;
