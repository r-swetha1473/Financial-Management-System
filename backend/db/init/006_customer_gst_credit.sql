-- Additive GST + credit fields on existing customer_skg.
-- Does not rename the table. credit_limit is stored only — no enforcement yet.
-- API gstin maps to gst_number, same as vendors.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS gst_number VARCHAR(50);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(19,4);

INSERT INTO schema_migrations (filename)
VALUES ('006_customer_gst_credit.sql')
ON CONFLICT (filename) DO NOTHING;
