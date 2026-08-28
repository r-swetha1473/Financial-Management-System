-- Additive FKs from customer_skg to documents for photo / address-proof.
-- Do not drop the leftover BYTEA columns on customer_skg; they are no longer written.
-- Files live on documents.file_data keyed by storage_key; access is via authenticated download.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS photo_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
ALTER TABLE customer_skg ADD COLUMN IF NOT EXISTS address_proof_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;

INSERT INTO schema_migrations (filename)
VALUES ('012_customer_document_refs.sql')
ON CONFLICT (filename) DO NOTHING;
