-- SmartTap S5 Feature 1 (Phase B): WhatsApp bot pending actions (confirmation)
-- Apply AFTER 009_review_responses.sql

-- A write action the owner asked for, held pending an explicit confirmation
-- ("reply SIM"). Shape: {tool, args..., summary}. expires_at gives it a short
-- TTL so a stale "SIM" hours later doesn't fire an action the owner forgot.
ALTER TABLE whatsapp_links
    ADD COLUMN IF NOT EXISTS pending_action JSONB,
    ADD COLUMN IF NOT EXISTS pending_action_expires_at TIMESTAMPTZ;
