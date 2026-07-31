-- SmartTap: Instagram DM assistant removed (2026-07-31).
-- Apply AFTER 019_business_type_restaurant.sql and AFTER the code removal
-- (commit b7e9f15) is deployed — the app must no longer reference these.
--
-- Drops the storage created by 016_instagram_dm.sql + 017_instagram_page_picker.sql.
-- ⚠️ tenants.opening_hours / menu_info / brand_voice (added in 016) SURVIVE —
-- the reviews module uses them for AI reply drafting.

-- RPCs first (they reference the tables).
DROP FUNCTION IF EXISTS meta_conn_upsert(uuid, text, text, text, text, text, text);
DROP FUNCTION IF EXISTS meta_conn_get(uuid, text);
DROP FUNCTION IF EXISTS meta_conn_get_by_ig(text, text);
DROP FUNCTION IF EXISTS meta_pending_upsert(uuid, text, jsonb, text);
DROP FUNCTION IF EXISTS meta_pending_get(uuid, text);

DROP TABLE IF EXISTS instagram_interactions;
DROP TABLE IF EXISTS meta_pending_connections;
DROP TABLE IF EXISTS tenant_meta_connections;
