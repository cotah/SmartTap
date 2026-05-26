-- SmartTap S4-W2: reactivation email tracking
-- Apply AFTER 004_campaigns_indexes.sql

-- When the daily cron sent a reactivation email to this customer. Used to
-- enforce a per-customer cooldown (90 days) so we don't spam someone who
-- simply isn't coming back. NULL means we've never emailed them.
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS last_reactivation_sent_at TIMESTAMPTZ;

-- Cron scan filters by tenant_id + last_visit_at < cutoff. The existing
-- single-column tenant_id index helps with selectivity; this composite
-- one lets the planner short-circuit straight to the inactive set.
CREATE INDEX IF NOT EXISTS idx_customers_tenant_last_visit
    ON customers(tenant_id, last_visit_at)
    WHERE email IS NOT NULL AND gdpr_consent = TRUE;
