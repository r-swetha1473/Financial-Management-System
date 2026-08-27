-- Additive: org-scoped document counters.
-- Does not change existing number columns or endpoints.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_sequences (
    organization_id UUID NOT NULL REFERENCES organizations(id),
    doc_type        VARCHAR(50) NOT NULL,
    current_number  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (organization_id, doc_type)
);

INSERT INTO schema_migrations (filename)
VALUES ('003_document_sequences.sql')
ON CONFLICT (filename) DO NOTHING;
