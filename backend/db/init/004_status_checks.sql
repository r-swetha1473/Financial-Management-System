-- Additive CHECK constraints matching Angular status unions.
-- Does not add columns, rename amounts, or convert VARCHAR to ENUM.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE p2p_purchase_requests DROP CONSTRAINT IF EXISTS p2p_purchase_requests_status_check;
ALTER TABLE p2p_purchase_requests
    ADD CONSTRAINT p2p_purchase_requests_status_check
    CHECK (status IN ('draft','submitted','approved','rejected','converted'));

ALTER TABLE p2p_purchase_orders DROP CONSTRAINT IF EXISTS p2p_purchase_orders_status_check;
ALTER TABLE p2p_purchase_orders
    ADD CONSTRAINT p2p_purchase_orders_status_check
    CHECK (status IN ('draft','issued','received','closed','cancelled'));

ALTER TABLE p2p_goods_receipts DROP CONSTRAINT IF EXISTS p2p_goods_receipts_status_check;
ALTER TABLE p2p_goods_receipts
    ADD CONSTRAINT p2p_goods_receipts_status_check
    CHECK (status IN ('received','cancelled'));

ALTER TABLE p2p_supplier_invoices DROP CONSTRAINT IF EXISTS p2p_supplier_invoices_status_check;
ALTER TABLE p2p_supplier_invoices
    ADD CONSTRAINT p2p_supplier_invoices_status_check
    CHECK (status IN ('pending','partially_paid','paid','cancelled'));

ALTER TABLE p2p_supplier_invoices DROP CONSTRAINT IF EXISTS p2p_supplier_invoices_approval_status_check;
ALTER TABLE p2p_supplier_invoices
    ADD CONSTRAINT p2p_supplier_invoices_approval_status_check
    CHECK (approval_status IN ('pending','approved','rejected'));

ALTER TABLE p2p_payments DROP CONSTRAINT IF EXISTS p2p_payments_status_check;
ALTER TABLE p2p_payments
    ADD CONSTRAINT p2p_payments_status_check
    CHECK (status IN ('completed','cancelled'));

ALTER TABLE payables DROP CONSTRAINT IF EXISTS payables_status_check;
ALTER TABLE payables
    ADD CONSTRAINT payables_status_check
    CHECK (status IN ('open','partial','closed'));

ALTER TABLE o2c_quotations DROP CONSTRAINT IF EXISTS o2c_quotations_status_check;
ALTER TABLE o2c_quotations
    ADD CONSTRAINT o2c_quotations_status_check
    CHECK (status IN ('draft','sent','accepted','rejected','converted'));

ALTER TABLE o2c_sales_orders DROP CONSTRAINT IF EXISTS o2c_sales_orders_status_check;
ALTER TABLE o2c_sales_orders
    ADD CONSTRAINT o2c_sales_orders_status_check
    CHECK (status IN ('confirmed','fulfilled','cancelled'));

ALTER TABLE o2c_deliveries DROP CONSTRAINT IF EXISTS o2c_deliveries_status_check;
ALTER TABLE o2c_deliveries
    ADD CONSTRAINT o2c_deliveries_status_check
    CHECK (status IN ('delivered','cancelled'));

ALTER TABLE o2c_sales_invoices DROP CONSTRAINT IF EXISTS o2c_sales_invoices_status_check;
ALTER TABLE o2c_sales_invoices
    ADD CONSTRAINT o2c_sales_invoices_status_check
    CHECK (status IN ('pending','partially_paid','paid','cancelled'));

ALTER TABLE o2c_collections DROP CONSTRAINT IF EXISTS o2c_collections_status_check;
ALTER TABLE o2c_collections
    ADD CONSTRAINT o2c_collections_status_check
    CHECK (status IN ('completed','cancelled'));

ALTER TABLE receivables DROP CONSTRAINT IF EXISTS receivables_status_check;
ALTER TABLE receivables
    ADD CONSTRAINT receivables_status_check
    CHECK (status IN ('open','partial','closed'));

ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_status_check;
ALTER TABLE expenses
    ADD CONSTRAINT expenses_status_check
    CHECK (status IN ('pending','approved','rejected'));

INSERT INTO schema_migrations (filename)
VALUES ('004_status_checks.sql')
ON CONFLICT (filename) DO NOTHING;
