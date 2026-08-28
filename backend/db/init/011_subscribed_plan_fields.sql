-- Additive subscribed-plan metadata on existing o2c_quotations.
-- Does not rename the table. plan_duration unit is days.
-- billing_cycle is stored only — it does not generate recurring invoices.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE o2c_quotations ADD COLUMN IF NOT EXISTS plan_duration INTEGER;
ALTER TABLE o2c_quotations ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20);
ALTER TABLE o2c_quotations ADD COLUMN IF NOT EXISTS deposit_amount NUMERIC(19,4) NOT NULL DEFAULT 0;

ALTER TABLE o2c_quotations DROP CONSTRAINT IF EXISTS o2c_quotations_plan_duration_check;
ALTER TABLE o2c_quotations
    ADD CONSTRAINT o2c_quotations_plan_duration_check
    CHECK (plan_duration IS NULL OR plan_duration > 0);

ALTER TABLE o2c_quotations DROP CONSTRAINT IF EXISTS o2c_quotations_billing_cycle_check;
ALTER TABLE o2c_quotations
    ADD CONSTRAINT o2c_quotations_billing_cycle_check
    CHECK (billing_cycle IS NULL OR billing_cycle IN ('one_time','weekly','monthly'));

INSERT INTO schema_migrations (filename)
VALUES ('011_subscribed_plan_fields.sql')
ON CONFLICT (filename) DO NOTHING;
