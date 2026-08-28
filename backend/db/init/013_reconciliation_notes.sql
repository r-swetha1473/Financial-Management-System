-- Manual notes only. Not a bank feed or matching engine.
CREATE TABLE IF NOT EXISTS reconciliation_notes (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id),
    note            TEXT NOT NULL DEFAULT '',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
