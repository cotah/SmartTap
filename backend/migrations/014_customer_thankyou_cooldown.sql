-- SmartTap: post-visit thank-you email tracking
-- Apply AFTER 013_nfc_tag_number.sql

-- When we last sent the automatic "thanks for visiting" email to this customer.
-- Unlike reactivation (dormant, 90-day cooldown) and review-nudge (24h-7d after
-- a tap, 30-day cooldown), this email fires in real time the moment a tap earns
-- a stamp. The cooldown here is short (6 hours) and exists only to dedupe: a
-- customer who taps twice in one visit, or genuinely returns the same day,
-- shouldn't get two thank-yous. NULL means we've never sent one. Distinct column
-- from the other two flows — independent triggers, cadences, and content.
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS last_thankyou_sent_at TIMESTAMPTZ;

-- The thank-you path is real-time and single-customer (no batch scan), so it
-- reads the cooldown straight off the customer row it already holds — no query
-- needs this column as a filter. A plain index keeps any future "who did we
-- thank recently" reporting cheap without the partial-index machinery the cron
-- flows use.
CREATE INDEX IF NOT EXISTS idx_customers_tenant_thankyou
    ON customers(tenant_id, last_thankyou_sent_at)
    WHERE email IS NOT NULL AND gdpr_consent = TRUE;
