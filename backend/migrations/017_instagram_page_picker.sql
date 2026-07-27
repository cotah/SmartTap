-- SmartTap Instagram Page Picker: let the owner choose which Facebook Page /
-- Instagram account to connect when their Facebook user manages more than one.
-- Apply AFTER 016_instagram_dm.sql.
--
-- Two pieces:
--   1. tenant_meta_connections gains page_name + ig_username so the dashboard
--      can show WHICH account is connected (before this, only numeric ids).
--   2. meta_pending_connections holds the OAuth user token (encrypted, short
--      TTL) between the callback detecting multiple pages and the owner
--      picking one in the dashboard. Display data lives in a jsonb column;
--      page access tokens are NEVER stored here — the select endpoint
--      re-resolves them from the user token.

-- ============================================================
-- tenant_meta_connections — display columns
-- ============================================================
ALTER TABLE tenant_meta_connections ADD COLUMN IF NOT EXISTS page_name   TEXT;
ALTER TABLE tenant_meta_connections ADD COLUMN IF NOT EXISTS ig_username TEXT;

-- ============================================================
-- meta_pending_connections — one pending OAuth selection per tenant
-- ============================================================
CREATE TABLE meta_pending_connections (
    tenant_id  UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    user_token BYTEA NOT NULL,   -- pgp_sym_encrypt output (long-lived user token)
    pages      JSONB NOT NULL,   -- [{facebook_page_id, page_name, instagram_business_account_id, ig_username}]
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE meta_pending_connections ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- pgcrypto RPCs
-- ============================================================

-- meta_conn_upsert/get gain the display columns; Postgres would otherwise
-- create overloads alongside the 016 signatures, so drop those first.
DROP FUNCTION meta_conn_upsert(uuid, text, text, text, text);
DROP FUNCTION meta_conn_get(uuid, text);

CREATE FUNCTION meta_conn_upsert(
    p_tenant_id         uuid,
    p_ig_account_id     text,
    p_facebook_page_id  text,
    p_page_access_token text,
    p_key               text,
    p_page_name         text DEFAULT NULL,
    p_ig_username       text DEFAULT NULL
) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    INSERT INTO tenant_meta_connections
        (tenant_id, instagram_business_account_id, facebook_page_id,
         page_access_token, page_name, ig_username)
    VALUES
        (p_tenant_id, p_ig_account_id, p_facebook_page_id,
         pgp_sym_encrypt(p_page_access_token, p_key), p_page_name, p_ig_username)
    ON CONFLICT (tenant_id) DO UPDATE
       SET instagram_business_account_id = EXCLUDED.instagram_business_account_id,
           facebook_page_id              = EXCLUDED.facebook_page_id,
           page_access_token             = EXCLUDED.page_access_token,
           page_name                     = EXCLUDED.page_name,
           ig_username                   = EXCLUDED.ig_username;
$$;

CREATE FUNCTION meta_conn_get(p_tenant_id uuid, p_key text)
RETURNS TABLE(
    tenant_id                     uuid,
    instagram_business_account_id text,
    facebook_page_id              text,
    page_access_token             text,
    connected_at                  timestamptz,
    page_name                     text,
    ig_username                   text
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           instagram_business_account_id,
           facebook_page_id,
           pgp_sym_decrypt(page_access_token, p_key),
           connected_at,
           page_name,
           ig_username
    FROM tenant_meta_connections
    WHERE tenant_id = p_tenant_id;
$$;

-- Pending selection: encrypt-on-write, 10-minute TTL enforced on read.
CREATE FUNCTION meta_pending_upsert(
    p_tenant_id  uuid,
    p_user_token text,
    p_pages      jsonb,
    p_key        text
) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    INSERT INTO meta_pending_connections (tenant_id, user_token, pages, expires_at)
    VALUES (p_tenant_id, pgp_sym_encrypt(p_user_token, p_key), p_pages,
            now() + interval '10 minutes')
    ON CONFLICT (tenant_id) DO UPDATE
       SET user_token = EXCLUDED.user_token,
           pages      = EXCLUDED.pages,
           created_at = now(),
           expires_at = EXCLUDED.expires_at;
$$;

CREATE FUNCTION meta_pending_get(p_tenant_id uuid, p_key text)
RETURNS TABLE(
    tenant_id  uuid,
    user_token text,
    pages      jsonb
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           pgp_sym_decrypt(user_token, p_key),
           pages
    FROM meta_pending_connections
    WHERE tenant_id = p_tenant_id
      AND expires_at > now();
$$;

-- Same lockdown discipline as 016: decrypt paths reachable only by the backend.
REVOKE EXECUTE ON FUNCTION meta_conn_upsert(uuid, text, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION meta_conn_get(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION meta_pending_upsert(uuid, text, jsonb, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION meta_pending_get(uuid, text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION meta_conn_upsert(uuid, text, text, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION meta_conn_get(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION meta_pending_upsert(uuid, text, jsonb, text) TO service_role;
GRANT EXECUTE ON FUNCTION meta_pending_get(uuid, text) TO service_role;
