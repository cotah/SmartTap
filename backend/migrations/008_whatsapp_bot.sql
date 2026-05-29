-- SmartTap S5 Feature 1 (Phase A): WhatsApp owner bot — auth/OTP tables
-- Apply AFTER 007_customers_review_nudge.sql

-- Links an owner's WhatsApp number to a tenant and tracks the auth state
-- machine. tenant_id stays NULL until the OTP is verified. One row per phone
-- (UNIQUE) — a number belongs to at most one tenant.
CREATE TABLE whatsapp_links (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone         TEXT NOT NULL UNIQUE,            -- E.164, e.g. +3538...
    tenant_id     UUID REFERENCES tenants(id) ON DELETE CASCADE,
    state         TEXT NOT NULL DEFAULT 'awaiting_email',
                  -- awaiting_email | awaiting_code | verified
    pending_email TEXT,                            -- email under verification
    verified_at   TIMESTAMPTZ,
    lockout_until TIMESTAMPTZ,                      -- anti-abuse temporary block
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_whatsapp_links_updated BEFORE UPDATE ON whatsapp_links
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- One-time codes emailed during owner verification. Stored hashed only.
CREATE TABLE whatsapp_otp_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone       TEXT NOT NULL,
    email       TEXT NOT NULL,
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    code_hash   TEXT NOT NULL,                      -- sha256(code)
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INT NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Latest-code lookup per phone + rate-limit window scan.
CREATE INDEX idx_whatsapp_otp_phone ON whatsapp_otp_codes(phone, created_at DESC);

-- RLS — backend uses the service_role key (bypasses RLS), but we keep the
-- policy gate on like every other table so a future anon-key path stays safe.
ALTER TABLE whatsapp_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_otp_codes ENABLE ROW LEVEL SECURITY;
