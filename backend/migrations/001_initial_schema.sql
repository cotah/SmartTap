-- SmartTap initial schema (v1)
-- Apply with: supabase db push  OR  paste in Supabase SQL editor.

-- ============================================================
-- tenants — one row per business customer
-- ============================================================
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    business_type   TEXT NOT NULL CHECK (business_type IN ('barbershop','cafe','pet_grooming','salon','tattoo','other')),
    logo_url        TEXT,
    primary_color   TEXT NOT NULL DEFAULT '#1B4D3E',
    accent_color    TEXT NOT NULL DEFAULT '#E8A020',
    google_place_id TEXT,
    google_review_url TEXT,
    google_business_url TEXT,
    stamps_for_reward INT NOT NULL DEFAULT 10,
    reward_description TEXT,
    reward_expires_days INT NOT NULL DEFAULT 30,
    stamp_rate_limit_minutes INT NOT NULL DEFAULT 120,
    plan            TEXT NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial','review','loyalty','pro','network')),
    is_founding_member BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    trial_ends_at   TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_stripe_customer ON tenants(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- ============================================================
-- tenant_members — users that administer a tenant
-- ============================================================
CREATE TABLE tenant_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner','staff')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, user_id)
);
CREATE INDEX idx_tenant_members_user ON tenant_members(user_id);

-- ============================================================
-- nfc_tags
-- ============================================================
CREATE TABLE nfc_tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tag_uuid        UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    format          TEXT CHECK (format IN ('counter_stand','table_tent','wall_plaque','sticker')),
    color           TEXT,
    location_name   TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    deployed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_nfc_tags_tenant ON nfc_tags(tenant_id);
CREATE INDEX idx_nfc_tags_uuid ON nfc_tags(tag_uuid);

-- ============================================================
-- customers — end customers of the tenant
-- ============================================================
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone           TEXT,
    email           TEXT,
    name            TEXT,
    birthday        DATE,
    magic_link_token TEXT UNIQUE,
    gdpr_consent    BOOLEAN NOT NULL DEFAULT FALSE,
    gdpr_consent_at TIMESTAMPTZ,
    gdpr_consent_text TEXT,
    total_visits    INT NOT NULL DEFAULT 0,
    total_stamps    INT NOT NULL DEFAULT 0,
    current_stamps  INT NOT NULL DEFAULT 0,
    last_visit_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, phone)
);
CREATE INDEX idx_customers_tenant ON customers(tenant_id);
CREATE INDEX idx_customers_phone ON customers(tenant_id, phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_customers_magic_link ON customers(magic_link_token) WHERE magic_link_token IS NOT NULL;
CREATE INDEX idx_customers_last_visit ON customers(tenant_id, last_visit_at DESC);

-- ============================================================
-- taps — every interaction
-- ============================================================
CREATE TABLE taps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id          UUID NOT NULL REFERENCES nfc_tags(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id     UUID REFERENCES customers(id) ON DELETE SET NULL,
    device_type     TEXT CHECK (device_type IN ('ios','android','other','unknown')),
    interaction_type TEXT CHECK (interaction_type IN ('nfc','qr')),
    action_taken    TEXT,
    user_agent      TEXT,
    ip_hash         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_taps_tenant_created ON taps(tenant_id, created_at DESC);
CREATE INDEX idx_taps_customer ON taps(customer_id) WHERE customer_id IS NOT NULL;
CREATE INDEX idx_taps_tag ON taps(tag_id);

-- ============================================================
-- stamps — one row per awarded stamp
-- ============================================================
CREATE TABLE stamps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tap_id          UUID REFERENCES taps(id) ON DELETE SET NULL,
    multiplier      INT NOT NULL DEFAULT 1,
    awarded_by      TEXT NOT NULL DEFAULT 'auto' CHECK (awarded_by IN ('auto','manual')),
    awarded_by_user UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_stamps_customer ON stamps(customer_id, created_at DESC);
CREATE INDEX idx_stamps_tenant_created ON stamps(tenant_id, created_at DESC);

-- ============================================================
-- rewards — generated when customer hits threshold
-- ============================================================
CREATE TABLE rewards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stamps_used     INT NOT NULL,
    description     TEXT NOT NULL,
    validation_code TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    redeemed_at     TIMESTAMPTZ,
    redeemed_by_user UUID REFERENCES auth.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, validation_code)
);
CREATE INDEX idx_rewards_customer ON rewards(customer_id, created_at DESC);
CREATE INDEX idx_rewards_tenant_status ON rewards(tenant_id, redeemed_at, expires_at);
CREATE INDEX idx_rewards_validation ON rewards(tenant_id, validation_code);

-- ============================================================
-- campaigns (Phase 2 — schema ready, feature disabled)
-- ============================================================
CREATE TABLE campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    type            TEXT CHECK (type IN ('double_stamp','reactivation','birthday','custom')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','paused','ended')),
    config          JSONB NOT NULL DEFAULT '{}',
    sent_count      INT NOT NULL DEFAULT 0,
    starts_at       TIMESTAMPTZ,
    ends_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_campaigns_tenant ON campaigns(tenant_id);

-- ============================================================
-- updated_at triggers
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_customers_updated BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
