-- SmartTap S4-W4: customer segmentation
-- Apply AFTER 005_customers_reactivation.sql

-- Reusable groups of customers defined by structured criteria. The criteria
-- live in JSONB rather than a wide column set because:
--   1. The shape evolves quickly (we expect to add criteria over the next
--      sprints — birthday window, preferred tags, campaign exposure).
--   2. The set is small and the engine reads + interprets it in Python; no
--      DB-side filtering on the JSON payload is needed.
--   3. Adding a new criterion stays a backend deploy, no migration churn.
--
-- The schema is intentionally minimal. We do NOT persist the resolved
-- customer set — segments are re-evaluated on demand. A merchant editing
-- the criteria sees fresh numbers without us running a sync job.
CREATE TABLE customer_segments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    -- See app/schemas/segment.py for the structure; validated at the API
    -- boundary so the DB stores only well-formed payloads.
    criteria        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every read is tenant-scoped (dashboard list, preview eval). The ordering
-- index gives "most recently created first" for free in the list query.
CREATE INDEX idx_customer_segments_tenant_created
    ON customer_segments(tenant_id, created_at DESC);

-- Updated-at trigger mirrors the pattern from 001.
CREATE TRIGGER trg_customer_segments_updated BEFORE UPDATE ON customer_segments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS — same tenant-isolation pattern as customers/campaigns/etc. Backend
-- uses the service_role key and bypasses RLS, but we keep the policies
-- defined so direct dashboard queries via the anon key (if ever wired up)
-- stay tenant-safe.
ALTER TABLE customer_segments ENABLE ROW LEVEL SECURITY;

CREATE POLICY customer_segments_all ON customer_segments FOR ALL
    USING (tenant_id IN (SELECT current_user_tenant_ids()));
