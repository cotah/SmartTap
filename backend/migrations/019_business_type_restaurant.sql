-- SmartTap: add 'restaurant' to the business_type CHECK (2026-07-29)
-- Apply AFTER 018_manual_reviews.sql
--
-- First restaurant tenant (Panda Restaurant) onboards; business_type feeds
-- the AI reply prompt ("a restaurant in Ireland"), so 'other' won't do.

ALTER TABLE tenants DROP CONSTRAINT tenants_business_type_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_business_type_check
    CHECK (business_type IN (
        'barbershop', 'cafe', 'pet_grooming', 'salon', 'tattoo',
        'restaurant', 'other'
    ));
