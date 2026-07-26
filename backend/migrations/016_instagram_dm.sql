-- SmartTap Instagram DM Assistant: per-tenant Meta connection + interaction log
-- + tenant context fields for the AI assistant. Apply AFTER 015_google_connection_account_name.sql.
--
-- Mirrors the Google Business pattern (009/011/015): the page_access_token is
-- encrypted at rest with pgcrypto and only accessible through SECURITY DEFINER
-- RPCs locked to service_role. The symmetric key lives ONLY in the backend env
-- (META_TOKEN_ENC_KEY) and is passed per call — never stored in the database.

-- ============================================================
-- tenants — context the DM assistant feeds into the AI prompt
-- ============================================================
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS opening_hours TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS menu_info     TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS brand_voice   TEXT;

-- ============================================================
-- tenant_meta_connections — one Meta (Facebook Page + IG) link per tenant
-- ============================================================
CREATE TABLE tenant_meta_connections (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                     UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    instagram_business_account_id TEXT NOT NULL,
    facebook_page_id              TEXT NOT NULL,
    page_access_token             BYTEA NOT NULL,  -- pgp_sym_encrypt output
    connected_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The webhook identifies the tenant by the IG business account id in the
-- payload — this lookup runs on every inbound DM.
CREATE INDEX idx_tmc_ig_account ON tenant_meta_connections(instagram_business_account_id);

CREATE TRIGGER trg_tmc_updated BEFORE UPDATE ON tenant_meta_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- instagram_interactions — log of every DM / story mention handled
-- ============================================================
CREATE TABLE instagram_interactions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    interaction_type   TEXT NOT NULL CHECK (interaction_type IN ('dm', 'story_mention')),
    external_sender_id TEXT NOT NULL,
    incoming_text      TEXT,
    reply_text         TEXT,
    status             TEXT NOT NULL DEFAULT 'answered'
                       CHECK (status IN ('answered', 'pending_approval', 'failed')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Monthly report counts by tenant + period; dashboard lists newest-first.
CREATE INDEX idx_ig_interactions_tenant_created
    ON instagram_interactions(tenant_id, created_at DESC);

-- ============================================================
-- pgcrypto RPCs (same discipline as google_conn_* in 011/015)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt-on-write upsert.
CREATE FUNCTION meta_conn_upsert(
    p_tenant_id         uuid,
    p_ig_account_id     text,
    p_facebook_page_id  text,
    p_page_access_token text,
    p_key               text
) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    INSERT INTO tenant_meta_connections
        (tenant_id, instagram_business_account_id, facebook_page_id, page_access_token)
    VALUES
        (p_tenant_id, p_ig_account_id, p_facebook_page_id,
         pgp_sym_encrypt(p_page_access_token, p_key))
    ON CONFLICT (tenant_id) DO UPDATE
       SET instagram_business_account_id = EXCLUDED.instagram_business_account_id,
           facebook_page_id              = EXCLUDED.facebook_page_id,
           page_access_token             = EXCLUDED.page_access_token;
$$;

-- Decrypt-on-read for one tenant (dashboard status + outbound sends).
CREATE FUNCTION meta_conn_get(p_tenant_id uuid, p_key text)
RETURNS TABLE(
    tenant_id                     uuid,
    instagram_business_account_id text,
    facebook_page_id              text,
    page_access_token             text,
    connected_at                  timestamptz
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           instagram_business_account_id,
           facebook_page_id,
           pgp_sym_decrypt(page_access_token, p_key),
           connected_at
    FROM tenant_meta_connections
    WHERE tenant_id = p_tenant_id;
$$;

-- Decrypt-on-read by IG business account id — the webhook's tenant lookup.
CREATE FUNCTION meta_conn_get_by_ig(p_ig_account_id text, p_key text)
RETURNS TABLE(
    tenant_id                     uuid,
    instagram_business_account_id text,
    facebook_page_id              text,
    page_access_token             text
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           instagram_business_account_id,
           facebook_page_id,
           pgp_sym_decrypt(page_access_token, p_key)
    FROM tenant_meta_connections
    WHERE instagram_business_account_id = p_ig_account_id;
$$;

-- Only the backend (service_role) may call these — the decrypt path must be
-- unreachable from the anon/authenticated dashboard keys.
REVOKE EXECUTE ON FUNCTION meta_conn_upsert(uuid, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION meta_conn_get(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION meta_conn_get_by_ig(text, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION meta_conn_upsert(uuid, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION meta_conn_get(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION meta_conn_get_by_ig(text, text) TO service_role;

-- RLS — backend uses the service-role key (bypasses); kept on for defence in
-- depth like every other table (same as 009).
ALTER TABLE tenant_meta_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE instagram_interactions ENABLE ROW LEVEL SECURITY;
