-- SmartTap S5 Feature 3: store the Google Business account name (for the
-- dashboard "Connected" badge) and surface connected_at on read.
-- Apply AFTER 014_customer_thankyou_cooldown.sql.
--
-- Extends the pgcrypto RPC trio from 011: the upsert gains p_account_name and
-- the read functions return account_name (+ connected_at on the single-tenant
-- get). Return-type and signature changes require DROP + CREATE (CREATE OR
-- REPLACE can't change them). Safe with the single existing row — its
-- account_name stays NULL until the owner reconnects.

ALTER TABLE tenant_google_connections
    ADD COLUMN IF NOT EXISTS account_name TEXT;

-- Encrypt-on-write upsert, now persisting account_name.
DROP FUNCTION IF EXISTS google_conn_upsert(uuid, text, text, text, text);
CREATE FUNCTION google_conn_upsert(
    p_tenant_id     uuid,
    p_refresh_token text,
    p_account_id    text,
    p_location_id   text,
    p_account_name  text,
    p_key           text
) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    INSERT INTO tenant_google_connections
        (tenant_id, refresh_token, account_id, location_id, account_name)
    VALUES
        (p_tenant_id, pgp_sym_encrypt(p_refresh_token, p_key),
         p_account_id, p_location_id, p_account_name)
    ON CONFLICT (tenant_id) DO UPDATE
       SET refresh_token = EXCLUDED.refresh_token,
           account_id    = EXCLUDED.account_id,
           location_id   = EXCLUDED.location_id,
           account_name  = EXCLUDED.account_name;
$$;

-- Decrypt-on-read for one tenant — now returns account_name + connected_at.
DROP FUNCTION IF EXISTS google_conn_get(uuid, text);
CREATE FUNCTION google_conn_get(p_tenant_id uuid, p_key text)
RETURNS TABLE(
    tenant_id     uuid,
    refresh_token text,
    account_id    text,
    location_id   text,
    account_name  text,
    connected_at  timestamptz
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           pgp_sym_decrypt(refresh_token, p_key),
           account_id,
           location_id,
           account_name,
           connected_at
    FROM tenant_google_connections
    WHERE tenant_id = p_tenant_id;
$$;

-- Decrypt-on-read for all tenants (review-responses cron) — now returns account_name.
DROP FUNCTION IF EXISTS google_conn_list(text);
CREATE FUNCTION google_conn_list(p_key text)
RETURNS TABLE(
    tenant_id     uuid,
    refresh_token text,
    account_id    text,
    location_id   text,
    account_name  text
)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           pgp_sym_decrypt(refresh_token, p_key),
           account_id,
           location_id,
           account_name
    FROM tenant_google_connections;
$$;

-- Re-lock the new signatures to service_role only (as in 011).
REVOKE EXECUTE ON FUNCTION google_conn_upsert(uuid, text, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION google_conn_get(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION google_conn_list(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION google_conn_upsert(uuid, text, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION google_conn_get(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION google_conn_list(text) TO service_role;
