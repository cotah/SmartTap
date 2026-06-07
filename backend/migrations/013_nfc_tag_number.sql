-- SmartTap: human-friendly NFC tag numbering. Apply AFTER
-- 012_customer_otp_codes.sql
--
-- Each tag gets a per-tenant sequential number (#1, #2, …) the owner can read
-- off the physical stand — distinct from tag_uuid, which is the opaque public
-- id on the chip. tag_uuid stays the routing key; tag_number is just a label.

ALTER TABLE nfc_tags ADD COLUMN tag_number INT;

-- Backfill existing tags: number them per tenant, oldest first, so current
-- stands get stable #1..#n in the order they were created.
UPDATE nfc_tags AS t
SET tag_number = sub.rn
FROM (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at, id) AS rn
    FROM nfc_tags
) AS sub
WHERE t.id = sub.id;

-- One number per tenant. Also the race guard: if two creates compute the same
-- next number, the second insert fails rather than duplicating.
CREATE UNIQUE INDEX idx_nfc_tags_tenant_number
    ON nfc_tags(tenant_id, tag_number);
