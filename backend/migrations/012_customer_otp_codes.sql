-- SmartTap Sprint 5.6: customer phone OTP — permanent identification without
-- cookies. Apply AFTER 011_encrypt_google_refresh_token.sql
--
-- A customer who cleared their browser / switched phones can reclaim their
-- account (and stamp history) by entering their phone and a 4-digit SMS code.
-- Codes are stored hashed only, short-lived, and rate-limited per phone+tenant.
-- A phone can belong to a different customer in each tenant, so rows are keyed
-- by (tenant_id, phone) — not phone alone like whatsapp_otp_codes (owner side).

CREATE TABLE customer_otp_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone       TEXT NOT NULL,                      -- E.164, e.g. +3538...
    code_hash   TEXT NOT NULL,                      -- sha256(tenant:phone:code)
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INT NOT NULL DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Latest-code lookup + per-phone rate-limit window scan, scoped to the tenant.
CREATE INDEX idx_customer_otp_phone
    ON customer_otp_codes(tenant_id, phone, created_at DESC);

-- RLS — backend uses the service_role key (bypasses RLS), but we keep the
-- gate on like every other table so a future anon-key path stays safe.
ALTER TABLE customer_otp_codes ENABLE ROW LEVEL SECURITY;
