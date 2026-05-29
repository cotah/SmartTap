-- SmartTap S5 audit follow-up 1: encrypt tenant_google_connections.refresh_token
-- at rest with pgcrypto. Apply AFTER 010_whatsapp_pending_actions.sql.
--
-- Safe with zero rows (Google not connected yet — build-to-activate). The
-- encryption key lives ONLY in the backend env (GOOGLE_TOKEN_ENC_KEY) and is
-- passed into the functions per call; it is never stored in the database.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- text -> bytea (holds pgp_sym_encrypt output). No rows to convert.
ALTER TABLE tenant_google_connections
    ALTER COLUMN refresh_token TYPE bytea USING convert_to(refresh_token, 'UTF8');

-- Encrypt-on-write upsert. SECURITY DEFINER so it runs as the table owner; we
-- lock EXECUTE down to service_role below.
CREATE OR REPLACE FUNCTION google_conn_upsert(
    p_tenant_id    uuid,
    p_refresh_token text,
    p_account_id   text,
    p_location_id  text,
    p_key          text
) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    INSERT INTO tenant_google_connections (tenant_id, refresh_token, account_id, location_id)
    VALUES (p_tenant_id, pgp_sym_encrypt(p_refresh_token, p_key), p_account_id, p_location_id)
    ON CONFLICT (tenant_id) DO UPDATE
       SET refresh_token = EXCLUDED.refresh_token,
           account_id    = EXCLUDED.account_id,
           location_id   = EXCLUDED.location_id;
$$;

-- Decrypt-on-read for one tenant.
CREATE OR REPLACE FUNCTION google_conn_get(p_tenant_id uuid, p_key text)
RETURNS TABLE(tenant_id uuid, refresh_token text, account_id text, location_id text)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           pgp_sym_decrypt(refresh_token, p_key),
           account_id,
           location_id
    FROM tenant_google_connections
    WHERE tenant_id = p_tenant_id;
$$;

-- Decrypt-on-read for all tenants (the review-responses cron iterates these).
CREATE OR REPLACE FUNCTION google_conn_list(p_key text)
RETURNS TABLE(tenant_id uuid, refresh_token text, account_id text, location_id text)
LANGUAGE sql SECURITY DEFINER SET search_path = public, extensions AS $$
    SELECT tenant_id,
           pgp_sym_decrypt(refresh_token, p_key),
           account_id,
           location_id
    FROM tenant_google_connections;
$$;

-- Only the backend (service_role) may call these. Anon/authenticated (dashboard
-- users via the anon key) must not be able to invoke the decrypt path at all.
REVOKE EXECUTE ON FUNCTION google_conn_upsert(uuid, text, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION google_conn_get(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION google_conn_list(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION google_conn_upsert(uuid, text, text, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION google_conn_get(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION google_conn_list(text) TO service_role;
