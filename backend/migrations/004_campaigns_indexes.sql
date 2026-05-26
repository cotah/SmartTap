-- SmartTap S4-W1: campaigns lookup performance
-- Apply AFTER 003_stripe_webhook_events.sql

-- Every NFC tap will look up "is there an active double_stamp campaign right
-- now for this tenant?". A composite index on (tenant_id, type, status) plus
-- a partial filter on status='active' keeps that lookup index-only and tiny
-- even when tenants accumulate dozens of ended campaigns.
CREATE INDEX IF NOT EXISTS idx_campaigns_tenant_type_active
    ON campaigns(tenant_id, type, starts_at, ends_at)
    WHERE status = 'active';
