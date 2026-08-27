# Architecture — Phase 1

No ERD file or PDF was present in the workspace. Analysis uses the entity list from the product specification. Existing table names are preserved; tenant and P2P/O2C entities are **additions**, not silent rewrites of existing relationships.

---

## A. Current project structure

Greenfield monorepo after Phase 1:

```
Financial Management System/
├── frontend/          Angular 20 standalone app
├── backend/           FastAPI + Pydantic + SQL init
├── docs/              Architecture and ERD notes
├── docker-compose.yml PostgreSQL 16
└── README.md
```

---

## B. Proposed frontend architecture

- Standalone Angular 20, lazy-loaded routes
- `core/` — auth, API client, RBAC, navigation, layout
- `shared/` — design-system components
- `features/` — dashboard, auth, P2P, O2C, modules, reports
- Services call `/api/v1/...`. When `useDevSeed` is true, HTTP failures fall back to the **same TypeScript contracts** (not a parallel mock app)
- Money display uses string formatting (`formatCurrencyInr`); charts convert to Number only for drawing

---

## C. Proposed backend architecture

```
backend/app/
  main.py
  core/       config, security, deps
  api/v1/     auth, dashboard, organizations
  schemas/    Pydantic camelCase aliases
  services/   Phase 1 seed (replace with DB in later phases)
backend/db/init/001_schema.sql
```

REST prefix: `/api/v1`. Status codes follow the product spec (200/201/400/401/403/404/409/422/500).

---

## D. Proposed database architecture

- PostgreSQL `NUMERIC(19,4)` for money — never `FLOAT`
- `organizations` is the tenant root
- Existing ERD names kept: `users`, `user_sessions`, `categories`, `subcategories`, `products`, `income_offering`, `vendors`, `expenses`, `invoice_skg`, `booking_skg`, `customer_skg`, `plan_skg`, `invoice_receipts`, `audit_logs`, `reference_data`
- **Added** `organization_id` on those tables (architecture gap in the original ERD)
- **Added** `documents` (BYTEA + `storage_key` for later object storage)
- **Added** P2P, O2C, finance account/transaction, payables, receivables tables

Existing FKs are not renamed. New FKs are additive.

---

## E. P2P module architecture

First-class navigation and schema:

Vendor → Purchase Request → Purchase Order → Goods/Service Receipt → Supplier Invoice → Approval → Payment → Payables

Tables: `p2p_purchase_requests`, `p2p_purchase_orders`, `p2p_goods_receipts`, `p2p_supplier_invoices`, `p2p_payments`, `payables`

Existing `expenses` remain for operational spend that is not yet a full P2P cycle. `purchase_order_number` on expenses can later link to `p2p_purchase_orders.po_number` without renaming the expenses table.

CRUD and matching rules: Phase 2.

---

## F. O2C module architecture

Customer → Quotation → Sales Order → Delivery/Service → Sales Invoice → Collection → Receivables

Tables: `o2c_quotations`, `o2c_sales_orders`, `o2c_deliveries`, `o2c_sales_invoices`, `o2c_collections`, `receivables`

Existing `invoice_skg`, `booking_skg`, `invoice_receipts` remain the current sales/billing records. O2C tables extend the product; they do not replace `_skg` tables until a mapping is approved.

CRUD and collection validation: Phase 3.

---

## G. Finance architecture

- `finance_accounts` — bank/cash
- `finance_transactions` — debit/credit
- GST fields stay on expenses (`gst_percentage`, `gst_amount`) and invoices (`is_gst_invoice`, `gst_amount`)
- Future GST reporting: CGST/SGST/IGST breakdown columns are **not** invented on existing tables; they will be added as a dedicated tax line structure when rules are defined
- Receipt creation remains transactional (lock invoice → sum receipts → validate outstanding → insert → audit → commit)

---

## H. Routing / navigation

Authenticated shell:

- Dashboard
- **P2P** (overview + six workflow screens)
- **O2C** (overview + six workflow screens)
- Finance (expenses, income, transactions, accounts, GST, reconciliation, bookings, invoices, receipts)
- Master data (vendors, customers, products, categories, services)
- Reports
- Administration (users, reference data, audit, documents, settings)

Public: `/login`, `/forgot-password`

---

## I. UI / design system

Custom CSS tokens (navy primary, white surfaces, semantic green/red/amber/purple). Shared components: shell, sidebar, topbar, page header, summary card, status badge, tables, empty/loading/error, toasts. P2P teal and O2C violet used only for workflow context.

---

## J. ERD gaps and required additions

| Gap | Action taken in Phase 1 schema |
|-----|--------------------------------|
| No tenant table | Added `organizations` |
| No `organization_id` on business tables | Added (does not change existing column names) |
| Users not tenant-scoped | `users.organization_id` + unique `(organization_id, email)` |
| No document metadata table | Added `documents` with BYTEA + storage_key |
| No explicit income ledger | Income still derived pending clarification; `income_offering` kept |
| No P2P/O2C entities | Added new tables; did not rename `invoice_skg` / `customer_skg` |
| `_skg` naming | Preserved in PostgreSQL; API uses `/invoices`, `/customers` |
| Unconfirmed FKs (expense→vendor, invoice→customer/booking/plan, booking→offering/customer) | Added as **proposed** FKs in SQL; confirm against official ERD before production migration |
| Invoice status / pending amount | Not stored as a new required column; compute from receipts until ERD confirms persistence |
| GST component split | Not added to existing expense/invoice rows |

**Do not treat `001_schema.sql` as a replacement ERD.** When the official ERD is supplied, compare FKs and drop or adjust only the additive proposals that conflict.

---

## K. Phase 1 implementation plan (done)

1. Monorepo + Docker PostgreSQL
2. FastAPI health, auth, dashboard, organization endpoints
3. Angular design system + shell + login + dashboard
4. P2P/O2C first-class navigation and workflow overviews
5. Tenant-aware session (`organizationId` / `organizationName`)
6. Schema foundation without renaming existing entities

### Later phases

- Phase 2: P2P CRUD + vendors
- Phase 3: O2C CRUD + customers/bookings/invoices/receipts
- Phase 4: Finance, GST reports, documents — see `docs/architecture/PHASE4-FINANCE.md`
- Phase 5: Users/roles UI, org management, audit — see `docs/architecture/PHASE5-ADMIN.md`
