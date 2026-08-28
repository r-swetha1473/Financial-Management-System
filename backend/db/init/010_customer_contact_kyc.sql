-- Additive contact + KYC fields on existing customer_skg.
-- Does not rename the table. File bytes stay on the row; API returns metadata only.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS drivers_license_number VARCHAR(100);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS photo_file_name VARCHAR(255);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS photo_mime_type VARCHAR(100);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS photo_file_size BIGINT;
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS photo_data BYTEA;
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS address_proof_file_name VARCHAR(255);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS address_proof_mime_type VARCHAR(100);
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS address_proof_file_size BIGINT;
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS address_proof_data BYTEA;

INSERT INTO schema_migrations (filename)
VALUES ('010_customer_contact_kyc.sql')
ON CONFLICT (filename) DO NOTHING;
