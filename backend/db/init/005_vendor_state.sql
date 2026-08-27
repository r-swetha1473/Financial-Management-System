-- Additive: optional vendor state for future GST reporting.
-- API gstin maps to the existing gst_number column — no duplicate GSTIN column.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE vendors ADD COLUMN IF NOT EXISTS state VARCHAR(100);

INSERT INTO schema_migrations (filename)
VALUES ('005_vendor_state.sql')
ON CONFLICT (filename) DO NOTHING;
