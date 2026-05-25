-- SmartTap RLS policies
-- Apply AFTER 001_initial_schema.sql

ALTER TABLE tenants            ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_members     ENABLE ROW LEVEL SECURITY;
ALTER TABLE nfc_tags           ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE taps               ENABLE ROW LEVEL SECURITY;
ALTER TABLE stamps             ENABLE ROW LEVEL SECURITY;
ALTER TABLE rewards            ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns          ENABLE ROW LEVEL SECURITY;

-- Helper: tenants the current authenticated user can administer
CREATE OR REPLACE FUNCTION current_user_tenant_ids()
RETURNS SETOF UUID
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
    SELECT tenant_id FROM tenant_members WHERE user_id = auth.uid();
$$;

-- tenants
CREATE POLICY tenants_select ON tenants FOR SELECT
    USING (id IN (SELECT current_user_tenant_ids()));
CREATE POLICY tenants_update ON tenants FOR UPDATE
    USING (id IN (SELECT current_user_tenant_ids()));

-- tenant_members
CREATE POLICY members_select ON tenant_members FOR SELECT
    USING (user_id = auth.uid() OR tenant_id IN (SELECT current_user_tenant_ids()));

-- Tenant-scoped policies (all rows have tenant_id)
CREATE POLICY customers_all ON customers FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

CREATE POLICY taps_all ON taps FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

CREATE POLICY stamps_all ON stamps FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

CREATE POLICY rewards_all ON rewards FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

CREATE POLICY nfc_tags_all ON nfc_tags FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

CREATE POLICY campaigns_all ON campaigns FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));

-- NOTE: backend FastAPI uses the Supabase service_role key, which BYPASSES RLS.
-- All publicly callable endpoints (/v1/taps/*, /v1/customers/identify) validate
-- tenant_id in application code before any operation.
