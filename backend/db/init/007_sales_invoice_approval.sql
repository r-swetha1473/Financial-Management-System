-- Additive approval_status on O2C sales invoices (same CHECK as supplier invoices).
-- Required before collections: only approved invoices can be collected against.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE o2c_sales_invoices
    ADD COLUMN IF NOT EXISTS approval_status VARCHAR(50) NOT NULL DEFAULT 'pending';

ALTER TABLE o2c_sales_invoices DROP CONSTRAINT IF EXISTS o2c_sales_invoices_approval_status_check;
ALTER TABLE o2c_sales_invoices
    ADD CONSTRAINT o2c_sales_invoices_approval_status_check
    CHECK (approval_status IN ('pending','approved','rejected'));

INSERT INTO schema_migrations (filename)
VALUES ('007_sales_invoice_approval.sql')
ON CONFLICT (filename) DO NOTHING;
