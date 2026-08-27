-- BFMS Phase 1: Core schema foundation
-- Preserves existing ERD entity names; adds organizations + P2P/O2C foundation

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TENANCY & AUTHENTICATION
-- ============================================================

CREATE TABLE IF NOT EXISTS organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    username        VARCHAR(100) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN','MANAGER','FINANCE','OPERATOR','VIEWER')),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, email)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    refresh_token   VARCHAR(512),
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- EXISTING ERD: MASTER DATA (with organization_id added)
-- ============================================================

CREATE TABLE IF NOT EXISTS categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subcategories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    category_id     UUID NOT NULL REFERENCES categories(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    vin_number      VARCHAR(100),
    model           VARCHAR(100),
    battery_type    VARCHAR(100),
    body_color      VARCHAR(100),
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS income_offering (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    product_id      UUID REFERENCES products(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    amount          NUMERIC(19,4) NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    address         TEXT,
    phone           VARCHAR(50),
    email           VARCHAR(255),
    poc_name        VARCHAR(255),
    poc_email       VARCHAR(255),
    gst_number      VARCHAR(50),
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_skg (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    address         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plan_skg (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    amount          NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS booking_skg (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    offering_id     UUID REFERENCES income_offering(id),
    customer_id     UUID REFERENCES customer_skg(id),
    booking_start_date DATE NOT NULL,
    booking_end_date   DATE,
    security_paid   NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    vendor_id       UUID REFERENCES vendors(id),
    category_id     UUID REFERENCES categories(id),
    subcategory_id  UUID REFERENCES subcategories(id),
    product_id      UUID REFERENCES products(id),
    product_service_name VARCHAR(255),
    sku             VARCHAR(100),
    quantity        NUMERIC(19,4) NOT NULL DEFAULT 1,
    unit_price      NUMERIC(19,4) NOT NULL DEFAULT 0,
    cost            NUMERIC(19,4) NOT NULL DEFAULT 0,
    gst_percentage  NUMERIC(5,2) NOT NULL DEFAULT 0,
    gst_amount      NUMERIC(19,4) NOT NULL DEFAULT 0,
    purchase_order_number VARCHAR(100),
    expense_date    DATE NOT NULL,
    entered_by      UUID REFERENCES users(id),
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoice_skg (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    invoice_number  VARCHAR(100) NOT NULL,
    customer_id     UUID REFERENCES customer_skg(id),
    booking_id      UUID REFERENCES booking_skg(id),
    plan_id         UUID REFERENCES plan_skg(id),
    invoice_raised_date DATE NOT NULL,
    security_amount_deposited NUMERIC(19,4) NOT NULL DEFAULT 0,
    invoice_amount  NUMERIC(19,4) NOT NULL DEFAULT 0,
    is_gst_invoice  BOOLEAN NOT NULL DEFAULT FALSE,
    gst_amount      NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS invoice_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    invoice_id      UUID NOT NULL REFERENCES invoice_skg(id),
    receipt_date    DATE NOT NULL,
    receipt_amount  NUMERIC(19,4) NOT NULL,
    pending_amount  NUMERIC(19,4) NOT NULL DEFAULT 0,
    payment_mode    VARCHAR(20) NOT NULL CHECK (payment_mode IN ('Cash','Card','UPI')),
    transaction_last4 VARCHAR(4),
    entered_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reference_data (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    data_type       VARCHAR(100) NOT NULL,
    code            VARCHAR(100) NOT NULL,
    label           VARCHAR(255) NOT NULL,
    metadata        JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, data_type, code)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    entity_name     VARCHAR(100) NOT NULL,
    entity_id       UUID,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    entity_name     VARCHAR(100) NOT NULL,
    entity_id       UUID NOT NULL,
    file_name       VARCHAR(255) NOT NULL,
    mime_type       VARCHAR(100) NOT NULL,
    file_size       BIGINT NOT NULL,
    storage_key     VARCHAR(512),
    file_data       BYTEA,
    uploaded_by     UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- P2P MODULE (Procure-to-Pay)
-- ============================================================

CREATE TABLE IF NOT EXISTS p2p_purchase_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    vendor_id       UUID REFERENCES vendors(id),
    request_number  VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    requested_by    UUID REFERENCES users(id),
    requested_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, request_number)
);

CREATE TABLE IF NOT EXISTS p2p_purchase_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    purchase_request_id UUID REFERENCES p2p_purchase_requests(id),
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    po_number       VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount    NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, po_number)
);

CREATE TABLE IF NOT EXISTS p2p_goods_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    purchase_order_id UUID NOT NULL REFERENCES p2p_purchase_orders(id),
    grn_number      VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'received',
    receipt_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, grn_number)
);

CREATE TABLE IF NOT EXISTS p2p_supplier_invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    vendor_id       UUID NOT NULL REFERENCES vendors(id),
    purchase_order_id UUID REFERENCES p2p_purchase_orders(id),
    goods_receipt_id UUID REFERENCES p2p_goods_receipts(id),
    invoice_number  VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    invoice_date    DATE NOT NULL,
    amount          NUMERIC(19,4) NOT NULL DEFAULT 0,
    gst_amount      NUMERIC(19,4) NOT NULL DEFAULT 0,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS p2p_payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    supplier_invoice_id UUID NOT NULL REFERENCES p2p_supplier_invoices(id),
    payment_date    DATE NOT NULL,
    amount          NUMERIC(19,4) NOT NULL,
    payment_mode    VARCHAR(20) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payables (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    source_type     VARCHAR(50) NOT NULL,
    source_id       UUID NOT NULL,
    vendor_id       UUID REFERENCES vendors(id),
    amount          NUMERIC(19,4) NOT NULL,
    outstanding     NUMERIC(19,4) NOT NULL,
    due_date        DATE,
    status          VARCHAR(50) NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- O2C MODULE (Order-to-Cash)
-- ============================================================

CREATE TABLE IF NOT EXISTS o2c_quotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    customer_id     UUID NOT NULL REFERENCES customer_skg(id),
    quote_number    VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'draft',
    quote_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until     DATE,
    total_amount    NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, quote_number)
);

CREATE TABLE IF NOT EXISTS o2c_sales_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    customer_id     UUID NOT NULL REFERENCES customer_skg(id),
    quotation_id    UUID REFERENCES o2c_quotations(id),
    order_number    VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'confirmed',
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount    NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, order_number)
);

CREATE TABLE IF NOT EXISTS o2c_deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    sales_order_id  UUID NOT NULL REFERENCES o2c_sales_orders(id),
    delivery_number VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'delivered',
    delivery_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, delivery_number)
);

CREATE TABLE IF NOT EXISTS o2c_sales_invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    customer_id     UUID NOT NULL REFERENCES customer_skg(id),
    sales_order_id  UUID REFERENCES o2c_sales_orders(id),
    delivery_id     UUID REFERENCES o2c_deliveries(id),
    invoice_number  VARCHAR(100) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    invoice_date    DATE NOT NULL,
    amount          NUMERIC(19,4) NOT NULL DEFAULT 0,
    gst_amount      NUMERIC(19,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (organization_id, invoice_number)
);

CREATE TABLE IF NOT EXISTS o2c_collections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    sales_invoice_id UUID NOT NULL REFERENCES o2c_sales_invoices(id),
    collection_date DATE NOT NULL,
    amount          NUMERIC(19,4) NOT NULL,
    payment_mode    VARCHAR(20) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'completed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS receivables (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    source_type     VARCHAR(50) NOT NULL,
    source_id       UUID NOT NULL,
    customer_id     UUID REFERENCES customer_skg(id),
    amount          NUMERIC(19,4) NOT NULL,
    outstanding     NUMERIC(19,4) NOT NULL,
    due_date        DATE,
    status          VARCHAR(50) NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- FINANCE MODULE
-- ============================================================

CREATE TABLE IF NOT EXISTS finance_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name            VARCHAR(255) NOT NULL,
    account_type    VARCHAR(50) NOT NULL CHECK (account_type IN ('bank','cash')),
    account_number  VARCHAR(100),
    balance         NUMERIC(19,4) NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS finance_transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    account_id      UUID NOT NULL REFERENCES finance_accounts(id),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('debit','credit')),
    amount          NUMERIC(19,4) NOT NULL,
    reference_type  VARCHAR(100),
    reference_id    UUID,
    description     TEXT,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    reconciled      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE finance_transactions
    ADD COLUMN IF NOT EXISTS reconciled BOOLEAN NOT NULL DEFAULT FALSE;

-- Seed demo organization (example tenant — not application identity)
INSERT INTO organizations (id, name, slug)
VALUES ('00000000-0000-0000-0000-000000000001', 'Demo Business Co.', 'demo-business')
ON CONFLICT (slug) DO NOTHING;
