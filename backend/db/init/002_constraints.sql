-- Additive constraints from the approved architecture review.
-- Does not add business tables. Safe to re-run.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One payable / receivable row per source document in an organization
CREATE UNIQUE INDEX IF NOT EXISTS payables_org_source_uidx
    ON payables (organization_id, source_type, source_id);

CREATE UNIQUE INDEX IF NOT EXISTS receivables_org_source_uidx
    ON receivables (organization_id, source_type, source_id);

-- Tenant filter indexes
CREATE INDEX IF NOT EXISTS users_organization_id_idx ON users (organization_id);
CREATE INDEX IF NOT EXISTS user_sessions_organization_id_idx ON user_sessions (organization_id);
CREATE INDEX IF NOT EXISTS user_sessions_user_id_idx ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS categories_organization_id_idx ON categories (organization_id);
CREATE INDEX IF NOT EXISTS subcategories_organization_id_idx ON subcategories (organization_id);
CREATE INDEX IF NOT EXISTS products_organization_id_idx ON products (organization_id);
CREATE INDEX IF NOT EXISTS income_offering_organization_id_idx ON income_offering (organization_id);
CREATE INDEX IF NOT EXISTS vendors_organization_id_idx ON vendors (organization_id);
CREATE INDEX IF NOT EXISTS customer_skg_organization_id_idx ON customer_skg (organization_id);
CREATE INDEX IF NOT EXISTS plan_skg_organization_id_idx ON plan_skg (organization_id);
CREATE INDEX IF NOT EXISTS booking_skg_organization_id_idx ON booking_skg (organization_id);
CREATE INDEX IF NOT EXISTS expenses_organization_id_idx ON expenses (organization_id);
CREATE INDEX IF NOT EXISTS expenses_vendor_id_idx ON expenses (vendor_id);
CREATE INDEX IF NOT EXISTS invoice_skg_organization_id_idx ON invoice_skg (organization_id);
CREATE INDEX IF NOT EXISTS invoice_receipts_organization_id_idx ON invoice_receipts (organization_id);
CREATE INDEX IF NOT EXISTS invoice_receipts_invoice_id_idx ON invoice_receipts (invoice_id);
CREATE INDEX IF NOT EXISTS reference_data_organization_id_idx ON reference_data (organization_id);
CREATE INDEX IF NOT EXISTS audit_logs_organization_id_idx ON audit_logs (organization_id);
CREATE INDEX IF NOT EXISTS documents_organization_id_idx ON documents (organization_id);
CREATE INDEX IF NOT EXISTS p2p_purchase_requests_organization_id_idx ON p2p_purchase_requests (organization_id);
CREATE INDEX IF NOT EXISTS p2p_purchase_orders_organization_id_idx ON p2p_purchase_orders (organization_id);
CREATE INDEX IF NOT EXISTS p2p_goods_receipts_organization_id_idx ON p2p_goods_receipts (organization_id);
CREATE INDEX IF NOT EXISTS p2p_supplier_invoices_organization_id_idx ON p2p_supplier_invoices (organization_id);
CREATE INDEX IF NOT EXISTS p2p_payments_organization_id_idx ON p2p_payments (organization_id);
CREATE INDEX IF NOT EXISTS p2p_payments_supplier_invoice_id_idx ON p2p_payments (supplier_invoice_id);
CREATE INDEX IF NOT EXISTS payables_organization_id_idx ON payables (organization_id);
CREATE INDEX IF NOT EXISTS o2c_quotations_organization_id_idx ON o2c_quotations (organization_id);
CREATE INDEX IF NOT EXISTS o2c_sales_orders_organization_id_idx ON o2c_sales_orders (organization_id);
CREATE INDEX IF NOT EXISTS o2c_deliveries_organization_id_idx ON o2c_deliveries (organization_id);
CREATE INDEX IF NOT EXISTS o2c_sales_invoices_organization_id_idx ON o2c_sales_invoices (organization_id);
CREATE INDEX IF NOT EXISTS o2c_collections_organization_id_idx ON o2c_collections (organization_id);
CREATE INDEX IF NOT EXISTS o2c_collections_sales_invoice_id_idx ON o2c_collections (sales_invoice_id);
CREATE INDEX IF NOT EXISTS receivables_organization_id_idx ON receivables (organization_id);
CREATE INDEX IF NOT EXISTS finance_accounts_organization_id_idx ON finance_accounts (organization_id);
CREATE INDEX IF NOT EXISTS finance_transactions_organization_id_idx ON finance_transactions (organization_id);
CREATE INDEX IF NOT EXISTS finance_transactions_account_id_idx ON finance_transactions (account_id);

ALTER TABLE p2p_payments DROP CONSTRAINT IF EXISTS p2p_payments_payment_mode_check;
ALTER TABLE p2p_payments
    ADD CONSTRAINT p2p_payments_payment_mode_check
    CHECK (payment_mode IN ('Cash','Card','UPI'));

ALTER TABLE o2c_collections DROP CONSTRAINT IF EXISTS o2c_collections_payment_mode_check;
ALTER TABLE o2c_collections
    ADD CONSTRAINT o2c_collections_payment_mode_check
    CHECK (payment_mode IN ('Cash','Card','UPI'));
