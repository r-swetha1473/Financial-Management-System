# Project state (as of 28 Aug 2026)

This document describes the **running codebase**, verified against FastAPI routers, services, and Angular routes. It is not a copy of `docs/DECISIONS.md`. Paths below are under `/api/v1` unless noted.

**How to read CRUD columns**

- **C** = `POST` exists and persists.
- **R** = list and/or get-by-id exist.
- **U** = body update (`PUT`/`PATCH` of the record). Approve/reject patches are **not** counted as Update.
- **D** = `DELETE` exists. **No business-record delete routes exist** anywhere (ADMIN has a `delete` permission that no route uses).

**RBAC shorthand.** Backend `require_permission(X)` maps to roles in `backend/app/core/rbac.py`. Tenant is always the JWT `organization_id` (`CurrentUser.tenant_id`). Request bodies cannot choose another org.

| Permission | Roles that pass |
|---|---|
| `view` | ADMIN, MANAGER, FINANCE, OPERATOR, VIEWER |
| `create` | ADMIN, MANAGER, FINANCE, OPERATOR |
| `edit` | ADMIN, MANAGER, FINANCE, OPERATOR |
| `approve` | ADMIN, MANAGER, FINANCE |
| `export` | ADMIN, MANAGER, FINANCE — **defined, unused on any API route**. Angular uses it only to show CSV export on live report views. |
| `delete` | ADMIN — **defined, unused on any API route**. |
| `admin` | ADMIN |
| `maintain_reference` | ADMIN, MANAGER |

Frontend `canMaintainReference` is ADMIN\|MANAGER (not a Permission string). Catalog SKUs stay on `create` so OPERATOR/FINANCE can add products.

---

## Contents

1. [Architecture overview](#1-architecture-overview)
2. [Module inventory](#2-module-inventory)
   - [2.0 Platform (auth, org, dashboard, documents)](#20-platform-auth-org-dashboard-documents)
   - [2.1 P2P](#21-p2p)
   - [2.2 O2C](#22-o2c)
   - [2.3 Finance](#23-finance)
   - [2.4 Master Data](#24-master-data)
   - [2.5 Admin](#25-admin)
   - [2.6 Reports](#26-reports)
3. [Workflow chains](#3-workflow-chains)
4. [RBAC matrix](#4-rbac-matrix)
5. [Known limitations by module](#5-known-limitations-by-module)
6. [Not yet implemented](#6-not-yet-implemented)

---

## 1. Architecture overview

```
Angular 20 (localhost:4200)
    HTTPS JSON, Bearer JWT
FastAPI  (`app.main:app`, prefix /api/v1, docs /api/docs)
    SQLAlchemy async
PostgreSQL 16
```

- **App name in UI:** LedgerFlow / KD Captain. API title: Business Financial Management System.
- **Tenant model:** one `organizations` row per tenant. Every user belongs to exactly one org. After login, every query is scoped with `organization_id` from the access token. Creating a second org is `POST /organizations` (ADMIN only); it does not switch the caller’s tenant.
- **Auth:** `POST /auth/login` issues access + refresh tokens. Access token carries `sub` (user id) and `organization_id`. `get_current_user` reloads the user from the DB and rejects inactive users / inactive orgs / token–user org mismatch.
- **Money:** `NUMERIC(19,4)` in Postgres; JSON serializers emit strings. P2P payments and O2C collections **do not** insert `finance_transactions` rows.
- **Schema:** SQL files in `backend/db/init/` applied at bootstrap. Alembic is in requirements but unused.
- **Health:** `GET /health` (no `/api/v1`, no auth) → `{ status, service }`.
- **Frontend environments:** `useDevSeed: false` in both `environment.ts` and `environment.prod.ts`. Login seed fallback and dashboard client fallback are **off**. Unused dashboard seed endpoints (`/products`, `/product/{id}`, `/categories`) still return fake rows if called directly (see §6); the UI does not call them.
- **UI list toolbar:** shared `FilterBarComponent` is live on P2P, O2C, Finance, Master Data, Admin, and Reports lists. Clear filters only appears when search or a select is active. Audit logs keep date-from/date-to on a second row (FilterBar has no date inputs).

---

## 2. Module inventory

### 2.0 Platform (auth, org, dashboard, documents)

Not a nav module, but these APIs are real.

#### Auth — prefix `/auth`

| Method | Path | What it does | Gate | C/R/U/D | Data |
|---|---|---|---|---|---|
| POST | `/auth/login` | Email/password → tokens + session | none | C (session) | Real users table |
| POST | `/auth/logout` | Revokes refresh sessions for the user | authenticated | — | Real |
| POST | `/auth/refresh` | New access token from refresh token | none (refresh token) | — | Real |
| GET | `/auth/session` | Current user from JWT | authenticated | R | Real |

**Update:** n/a. **Delete:** n/a.

Forgot-password **page exists** (`/forgot-password`). Submit shows a toast only — **no API**. See §6.

#### Organizations — prefix `/organizations`

| Method | Path | What it does | Gate | C/R/U/D | Data |
|---|---|---|---|---|---|
| GET | `/organizations/current` | Name/slug/active for the JWT org | authenticated | R | Real |
| POST | `/organizations` | Provision a new org + first admin user | `admin` | C | Real |
| PUT | `/organizations/current` | Rename / slug / active flag | `admin` | **U works** | Real |

#### Dashboard — prefix `/dashboard` (any authenticated user; no extra permission)

| Method | Path | What it does | Gate | Data |
|---|---|---|---|---|
| GET | `/dashboard/summary` | Five KPI cards: cash-basis net, collections, payments, expenses, receipts | authenticated | **Live** (`CashPositionService`) |
| GET | `/dashboard/cash-position` | Same formula broken into line items | authenticated | **Live** |
| GET | `/dashboard/income?period=` | Income/expense **trend chart** (daily 7 / weekly 4 / monthly 6 buckets) | authenticated | **Live** — same cash-basis sources as the KPI cards |
| GET | `/dashboard/expenses` | Last 8 expense debits (`finance_transactions`) | authenticated | **Live** |
| GET | `/dashboard/invoices` | Last 8 O2C sales invoices + legacy `invoice_skg` | authenticated | **Live** |
| GET | `/dashboard/receipts` | Last 8 completed collections + legacy `invoice_receipts` | authenticated | **Live** |
| GET | `/dashboard/products` | Product financial summary table | authenticated | **Seed** — **UI hidden**. No product-level revenue tracking. |
| GET | `/dashboard/product/{id}` | One seed product (or first seed row) | authenticated | **Seed** — unused by UI |
| GET | `/dashboard/categories` | Expense-by-category breakdown | authenticated | **Seed** — UI chart **removed**; do not wire this |

Angular calls summary, cash-position, income/trend, expenses, invoices, and receipts. It does **not** call products, product/{id}, or categories.

#### Documents — prefix `/documents`

| Method | Path | What it does | Gate | C/R/U/D | Data |
|---|---|---|---|---|---|
| GET | `/documents` | Paginated list for the org | `view` | R | Real BYTEA rows |
| POST | `/documents` | Upload PNG/JPEG/PDF, max 10 MB | `create` | C | Real |
| GET | `/documents/{id}` | Metadata | `view` | R | Real |
| GET | `/documents/{id}/content` | File bytes (tenant re-checked; no public URL) | `view` | R | Real |

**Update not supported** (no PUT). **Delete not supported**. Used for customer KYC and workspace uploads (`entityName=organization`).

---

### 2.1 P2P

Prefix `/p2p`. Vendors are also the Master Data “Vendors” screens (`/master/vendors`) hitting the same API.

#### Vendors — `/p2p/vendors`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/vendors` | List (`status`, `search` on name/email/GST) | `view` | R |
| GET | `/p2p/vendors/{id}` | Detail | `view` | R |
| POST | `/p2p/vendors` | Create | `maintain_reference` | C |

**Update:** no PUT. Angular `unsupportedUpdate` toast (“Updating a vendor is not supported by the API yet”). **Delete:** none. **Data:** real `vendors` table.

#### Purchase requests — `/p2p/purchase-requests`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/purchase-requests` | List (`vendor_id`, `status`, `search`) | `view` | R |
| GET | `/p2p/purchase-requests/{id}` | Detail | `view` | R |
| POST | `/p2p/purchase-requests` | Create (default status `draft`) | `create` | C |
| PUT | `/p2p/purchase-requests/{id}` | **Explicit 501** | `edit` | **U = 501** |
| PATCH | `/p2p/purchase-requests/{id}/approve` | `draft`/`submitted` → `approved` | `approve` | approve, not U |
| PATCH | `/p2p/purchase-requests/{id}/reject` | `draft`/`submitted` → `rejected` | `approve` | approve, not U |

**Update not supported (501)** — this is the **only** backend route that returns HTTP 501. Detail text: *Updating a purchase request is not supported. Approve or reject a draft or submitted request instead.*

**Data:** real.

#### Purchase orders — `/p2p/purchase-orders`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/purchase-orders` | List (`vendor_id`, `status`, `search`) | `view` | R |
| GET | `/p2p/purchase-orders/{id}` | Detail | `view` | R |
| POST | `/p2p/purchase-orders` | Create. Vendor required. PR optional; if present must be `approved`. | `create` | C |
| PATCH | `/p2p/purchase-orders/{id}/issue` | `draft` → `issued` only. Any other status is 400. | `create` | issue, not U |

**Update:** no PUT. Angular toast. **Delete:** none. Schema default status is `draft`. GRN requires `issued` (see §3). Convert-from-PR sets `issued`; a blank create form defaults to `draft`. Detail shows **Issue purchase order** for drafts (same `create` gate as PO create). **Record receipt** only when status is `issued`.

**Data:** real. On convert, PR status becomes `converted`.

#### Goods receipts — `/p2p/goods-receipts`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/goods-receipts` | List (`status`, `search`) | `view` | R |
| GET | `/p2p/goods-receipts/{id}` | Detail | `view` | R |
| POST | `/p2p/goods-receipts` | Create against a PO with status `issued`. Default GRN status `received`. | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none. Creating with status `received` sets the PO to `received`.

**Data:** real.

#### Supplier invoices — `/p2p/supplier-invoices`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/supplier-invoices` | List (`vendor_id`, `status`, `search`) | `view` | R |
| GET | `/p2p/supplier-invoices/{id}` | Detail | `view` | R |
| POST | `/p2p/supplier-invoices` | Create. **Requires a GRN with status `received`.** One SI per GRN. | `create` | C |
| PATCH | `.../{id}/approve` | `approval_status` → `approved` | `approve` | approve |
| PATCH | `.../{id}/reject` | `approval_status` → `rejected` | `approve` | approve |

Created as `status=pending`, `approval_status=pending`. **Update of amount/fields:** no PUT; Angular toast.

**Data:** real. Angular create form still offers PO-only invoicing; backend rejects it.

#### Payments — `/p2p/payments`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/payments` | List (`search`) | `view` | R |
| GET | `/p2p/payments/{id}` | Detail | `view` | R |
| POST | `/p2p/payments` | Pay an **approved** SI. Amount ≤ outstanding. Does **not** post to `finance_transactions`. | `create` | C |

**Update / Delete:** none. First payment **creates** the payable (`lock_or_create_for_invoice`); further payments update outstanding (`open` → `partial` → `closed`).

**Data:** real.

#### Payables — `/p2p/payables`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/p2p/payables` | List (`vendor_id`, `status`, `search`) | `view` | **R list only** |

No POST (system-created). **No GET by id.** Angular `/p2p/payables/:id` loads the row by listing `pageSize: 100` and finding the id — **will miss payables beyond the first 100**.

**Update / Delete:** none. **Data:** real.

---

### 2.2 O2C

Prefix `/o2c`. Customers are also Master Data “Customers” (`/master/customers`). UI name for quotations: **Subscribed Plans**. JSON still uses `quoteNumber` / `quotationId`.

#### Customers — `/o2c/customers`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/customers` | List (page only; no search param) | `view` | R |
| GET | `/o2c/customers/{id}` | Detail + KYC document refs | `view` | R |
| POST | `/o2c/customers` | Create | `maintain_reference` | C |

**Update:** no PUT. Angular toast. **Delete:** none. **Data:** real `customer_skg`.

#### Subscribed plans (quotations) — `/o2c/quotations`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/quotations` | List (`customer_id`, `status`, `search`) | `view` | R |
| GET | `/o2c/quotations/{id}` | Detail | `view` | R |
| POST | `/o2c/quotations` | Create. Default status `draft`. Status can be set on create (`accepted`, etc.). | `create` | C |
| PATCH | `/o2c/quotations/{id}/accept` | `draft` → `accepted` only | `approve` | approve, not U |
| PATCH | `/o2c/quotations/{id}/reject` | `draft` → `rejected` only | `approve` | approve, not U |

`sent` (and any non-draft) cannot be accepted or rejected — 400. Converting to an SO still requires status `accepted`. Detail **Accept** / **Reject** use `approve` (ADMIN/MANAGER/FINANCE), matching invoice approval — not `create`. **Create sales order** only when status is `accepted`.

**Update:** no PUT. Angular toast. **Delete:** none. `billing_cycle` is stored; it does not generate recurring invoices. `deposit_amount` is metadata only — not added to the sales invoice.

**Data:** real `o2c_quotations`.

#### Sales orders — `/o2c/sales-orders`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/sales-orders` | List (`customer_id`, `status`, `search`) | `view` | R |
| GET | `/o2c/sales-orders/{id}` | Detail | `view` | R |
| POST | `/o2c/sales-orders` | Create. Customer required. Plan optional; if present must be `accepted`. Default status `confirmed`. | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none. Convert sets plan status `converted`.

**Data:** real.

#### Deliveries — `/o2c/deliveries`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/deliveries` | List (page only) | `view` | R |
| GET | `/o2c/deliveries/{id}` | Detail | `view` | R |
| POST | `/o2c/deliveries` | Create against SO status `confirmed` or `fulfilled`. Default delivery status `delivered`. | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none. Status `delivered` sets SO to `fulfilled`.

**Data:** real.

#### Sales invoices — `/o2c/sales-invoices`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/sales-invoices` | List | `view` | R |
| GET | `/o2c/sales-invoices/{id}` | Detail + live outstanding | `view` | R |
| POST | `/o2c/sales-invoices` | Create. **Requires a delivery with status `delivered`.** One invoice per delivery. | `create` | C |
| PATCH | `.../{id}/approve` | `approval_status` → `approved` | `approve` | approve |
| PATCH | `.../{id}/reject` | `approval_status` → `rejected` | `approve` | approve |

Created `pending` / `pending`. **Update of fields:** no PUT; Angular toast. Deposit / booking security is **not** included in `amount`.

**Data:** real. Angular form still allows SO-only / customer-only invoicing; backend rejects it.

#### Collections — `/o2c/collections`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/collections` | List | `view` | R |
| GET | `/o2c/collections/{id}` | Detail | `view` | R |
| POST | `/o2c/collections` | Collect against an **approved** sales invoice. Does **not** post to `finance_transactions`. | `create` | C |

**Update / Delete:** none. Creates/updates the receivable the same way payments do for payables.

**Data:** real.

#### Receivables — `/o2c/receivables`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/o2c/receivables` | List | `view` | R |
| GET | `/o2c/receivables/{id}` | Detail | `view` | R |

No POST. Created by collections. **Update / Delete:** none. **Data:** real.

---

### 2.3 Finance

Prefix `/finance` except legacy bookings/invoices/receipts, which live at `/bookings`, `/invoices`, `/receipts` (no `/finance` prefix). Angular routes them under `/finance/...`.

#### Expenses — `/finance/expenses`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/expenses` | List | `view` | R |
| GET | `/finance/expenses/{id}` | Detail | `view` | R |
| POST | `/finance/expenses` | Debit `finance_transactions` (amount, date, description, optional vendor). First expense per org auto-creates **Operating cash**. | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none. **Data:** real. Form only shows stored fields (GST/category/SKU were removed from the form).

#### Accounts — `/finance/accounts`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/accounts` | List the implicit Operating cash row | `view` | R list |

Read-only. Balance shown in UI is CashPositionService net, **not** `finance_accounts.balance`. No create/update/delete.

**Data:** real row, derived display.

#### Transactions — `/finance/transactions`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/transactions` | List expense debits (`account_id`, `search`) | `view` | R list |

No create (created by expense POST). Payments/collections are **not** merged here.

**Data:** real.

#### Income — `/finance/income`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/income` | Cash-basis derived list: completed O2C collections + legacy `invoice_receipts` | `view` | R list |

No manual income POST. Accrual invoices are not listed.

**Data:** real, derived.

#### GST — `/finance/gst`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/gst/summary` | Input GST (non-cancelled SI) vs output GST (O2C SI + legacy GST invoices). Optional `date_from`/`date_to`. | `view` | R |

Flat `gst_amount` only. Expense GST = 0 (not stored). No tax engine.

**Data:** real aggregates.

#### Reconciliation — `/finance/reconciliation`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/finance/reconciliation/note` | One org-scoped free-text note | `view` | R |
| PUT | `/finance/reconciliation/note` | Save the note | `edit` | **U works** |

Does not match or post bank lines. UI is “not connected” plus the note.

**Data:** real `reconciliation_notes`.

#### Legacy bookings — `/bookings`, `/invoices`, `/receipts`

Parallel to O2C, not a replacement. `plan_skg` has **no API**; booking invoices send `planId: null`.

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/bookings` | List (`customer_id`) | `view` | R |
| GET | `/bookings/{id}` | Detail | `view` | R |
| POST | `/bookings` | Create | `create` | C |
| GET | `/invoices` | Legacy booking invoices (`customer_id`) | `view` | R |
| GET | `/invoices/{id}` | Detail | `view` | R |
| POST | `/invoices` | Create | `create` | C |
| GET | `/receipts` | Receipts against legacy invoices | `view` | R |
| GET | `/receipts/{id}` | Detail | `view` | R |
| POST | `/receipts` | Create; outstanding computed from stored receipts | `create` | C |

**Update:** no PUT. Angular toast on booking/invoice edit. **Delete:** none. Security/deposit on bookings is stored separately, not added into invoice amount.

**Data:** real `booking_skg` / `invoice_skg` / `invoice_receipts`.

---

### 2.4 Master Data

Nav: Vendors, Customers, Products, Categories, Services. Vendors/customers APIs are listed under P2P/O2C above.

UI create buttons:

- Vendors, customers: `canMaintainReference` (ADMIN/MANAGER). Detail shortcuts “New purchase request” / “New subscribed plan” use the same gate. OPERATOR/FINANCE still create PRs and plans from those modules’ list pages.
- Products, categories, services: `hasPermission(..., 'create')` — OPERATOR and FINANCE can add catalog rows.

#### Products — `/products`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/products` | List (`search`, `status`) | `view` | R |
| GET | `/products/{id}` | Detail | `view` | R |
| POST | `/products` | Create | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none. **Data:** real.

#### Categories — `/categories`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/categories` | List | `view` | R list (no get-by-id) |
| POST | `/categories` | Create | `create` | C |

**Update:** no PUT. Angular toast. **Delete:** none.

#### Subcategories — `/subcategories`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/subcategories` | List | `view` | R list |
| POST | `/subcategories` | Create | `create` | C |

Same update/delete story. Used from the Categories page.

#### Offerings (Services) — `/offerings`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/offerings` | List | `view` | R list |
| POST | `/offerings` | Create | `create` | C |

**Update:** no PUT. Angular toast. Booking create dropdown loads live offerings (pageSize 100).

#### Reference data — `/reference-data` (Admin nav, master-like)

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/reference-data` | List (`search`) | `view` | R list |
| POST | `/reference-data` | Create lookup row | `maintain_reference` | C |

**Update:** no PUT. Angular toast. **Delete:** none. **Data:** real.

---

### 2.5 Admin

Nav: Users (ADMIN only), Reference Data (ADMIN/MANAGER), Audit Logs (all roles), Documents (all), Settings (ADMIN only).

#### Users — `/admin/users`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/admin/users` | List (`search`, `status`, `role`) | `admin` | R |
| POST | `/admin/users` | Create user in this org | `admin` | C |
| PUT | `/admin/users/{id}` | Update name/email/role/active/password | `admin` | **U works** |

Last-admin and self-deactivate are blocked with row locks. **Delete:** none (deactivate instead).

**Data:** real.

#### Audit logs — `/admin/audit-logs`

| Method | Path | What it does | Gate | C/R/U/D |
|---|---|---|---|---|
| GET | `/admin/audit-logs` | Paginated org logs (`entity_name`, `action`, `actor_user_id`, `date_from`, `date_to`) | `view` (any signed-in role) | R |

Append-only (DB trigger). Vendor/customer/plan **creates are not audited** today. Payments, collections, approvals, expenses, admin user changes are.

**Data:** real. No POST/PUT/DELETE from the API.

#### Settings

Uses `GET`/`PUT /organizations/current` (see §2.0). **U works** for ADMIN.

#### Documents workspace

Uses `/documents` (see §2.0).

---

### 2.6 Reports

| Method | Path | What it does | Gate | Data |
|---|---|---|---|---|
| GET | `/reports/{key}` | One report view (KPIs + rows) | `view` | Live SQL **if** key is in the live set; otherwise 200 with empty stub *“This report is not in the live set.”* |

**Live keys** (Angular registers exactly these seven routes):

| Key (aliases) | Angular route | Source |
|---|---|---|
| `p2p`, `purchase` | `/reports/p2p` | POs + supplier invoices |
| `o2c`, `sales` | `/reports/o2c` | Plans + sales invoices |
| `payables` | `/reports/payables` | Payables outstanding |
| `receivables` | `/reports/receivables` | Receivables outstanding |
| `gst` | `/reports/gst` | Same GST summary as Finance |
| `cash-flow` | `/reports/cash-flow` | CashPositionService movement |
| `financial-summary`, `pnl` | `/reports/financial-summary` | Cash-basis P&L (same formula as dashboard net cash) |

CSV export is **client-side** (`export` permission). No report POST/PUT/DELETE.

Leftover `frontend/.../report.service.ts` still builds reports from **localStorage seed stores**. **Nothing injects it.** Live report views call `GET /reports/{key}`.

---

## 3. Workflow chains

### P2P

```
Vendor (required master)
    │
    ├─[optional]─ Purchase Request  status: draft | submitted
    │                  │
    │                  │ PATCH approve   (ADMIN / MANAGER / FINANCE)
    │                  │   draft|submitted → approved
    │                  │ PATCH reject → rejected  (dead end)
    │                  ▼
    │             convert to PO  (PR must be approved if linked)
    │
    ▼
Purchase Order  ── vendor required ── PR optional
    status on create: UI default draft; convert-from-PR sets issued
    │
    │ PATCH /issue  (create permission: ADMIN/MANAGER/FINANCE/OPERATOR)
    │   draft → issued  (any other status → 400)
    │ GRN requires PO status == issued
    ▼
Goods Receipt  default status received  (PO → received)
    │
    │ SI requires GRN status == received
    │ one SI per GRN  (PO-only invoicing is UI-only, backend 400)
    ▼
Supplier Invoice  status pending, approval_status pending
    │
    │ PATCH approve  (ADMIN / MANAGER / FINANCE)  → approval_status approved
    │ PATCH reject → rejected  (cannot pay)
    ▼
Payment  POST  (create permission; invoice must be approved)
    amount ≤ outstanding; not posted to finance_transactions
    │
    ▼
Payable  auto-created on first payment
    open → partial → closed at outstanding 0
```

**Required vs optional**

| Step | Required? |
|---|---|
| Vendor | **Required** for PO (and thus the rest of the chain) |
| Purchase request | **Optional.** If used, must be `approved` before convert |
| Purchase order | **Required** for GRN |
| PO status `issued` | **Required** for GRN |
| Goods receipt `received` | **Required** for SI |
| Supplier invoice | **Required** to pay |
| Invoice **approval** | **Required** before payment |
| Payment | Creates/updates payable |
| Payable | Not created by the user; no payable POST |

### O2C

```
Customer (required master)
    │
    ├─[optional]─ Subscribed Plan (o2c_quotations)
    │                  create status: UI default draft
    │                  PATCH /accept  (approve: ADMIN/MANAGER/FINANCE)  draft → accepted
    │                  PATCH /reject  draft → rejected  (dead end)
    │                  │
    │                  ▼ convert to SO  (plan must be accepted if linked)
    │
    ▼
Sales Order  ── customer required ── plan optional
    default status confirmed
    │
    │ Delivery requires SO confirmed | fulfilled
    ▼
Delivery / Service  default status delivered  (SO → fulfilled)
    │
    │ Sales invoice requires delivery status == delivered
    │ one invoice per delivery  (SO-only / customer-only is UI-only, backend 400)
    ▼
Sales Invoice  pending / pending
    │
    │ PATCH approve  (ADMIN / MANAGER / FINANCE)
    │ PATCH reject → cannot collect
    ▼
Collection  POST  (invoice must be approved)
    amount ≤ outstanding; not posted to finance_transactions
    deposit_amount / booking security_paid do NOT enter invoice amount
    │
    ▼
Receivable  auto-created on first collection
    open → partial → closed
```

**Required vs optional**

| Step | Required? |
|---|---|
| Customer | **Required** for SO |
| Subscribed plan | **Optional.** If used, must be `accepted` before convert |
| Sales order | **Required** for delivery |
| Delivery `delivered` | **Required** for sales invoice |
| Sales invoice | **Required** to collect |
| Invoice **approval** | **Required** before collection |
| Collection | Creates/updates receivable |
| Receivable | No user POST |
| Recurring invoices from `billing_cycle` | **Not implemented** — one invoice per plan |

O2C banner in the UI skips a separate “Approval” step; the API still requires it before collection.

**Legacy booking chain** (Finance, parallel): Booking → booking invoice → receipt. No GRN/delivery. Security paid is stored, not invoiced.

---

## 4. RBAC matrix

Who can **create / approve / pay / view** each category. “Pay” = POST payment or POST collection. VIEWER never creates.

| Category | ADMIN | MANAGER | FINANCE | OPERATOR | VIEWER |
|---|---|---|---|---|---|
| **Party data** (vendors, customers, reference data) | create + view | create + view | view only | view only | view only |
| **Catalog data** (products, categories, subcategories, offerings) | create + view | create + view | create + view | create + view | view only |
| **Operational documents** (PR, PO, GRN, SI, SO, delivery, sales invoice, expense, booking/invoice/receipt, documents upload) | create + view | create + view | create + view | create + view | view only |
| **Approve** (PR, subscribed plan accept/reject, supplier invoice, sales invoice) | yes | yes | yes | **no** | **no** |
| **Pay / collect** (P2P payment, O2C collection) | yes (create) | yes | yes | yes | **no** |
| **Payables / receivables / income / accounts / GST / reports / audit list** | view | view | view | view | view |
| **Admin actions** (users CRUD-via-PUT, org settings, provision org) | yes | **no** | **no** | **no** | **no** |
| **Reconciliation note** | view + **edit** | view + edit | view + edit | view + edit | view only |
| **Delete business records** | permission exists, **no routes** | — | — | — | — |

Detail-page shortcuts (vendor → new PR, customer → new plan) follow **party** rules (ADMIN/MANAGER), not operational `create`.

---

## 5. Known limitations by module

Each item is tagged **DELIBERATE SCOPE DECISION** or **KNOWN GAP TO FIX LATER**.

### P2P

- Supplier invoices require a received GRN; PO-only invoicing in the Angular form is rejected by the API. **DELIBERATE SCOPE DECISION**
- Purchase orders may be created without a PR; convert still needs PR `approved`. **DELIBERATE SCOPE DECISION**
- Record updates (vendor, PR body, PO, GRN, SI fields) are out of scope. PR is the only **HTTP 501** PUT; others have no PUT and the UI toasts. **DELIBERATE SCOPE DECISION**
- Payments do not post to `finance_transactions`. **DELIBERATE SCOPE DECISION**
- Create-form source dropdowns (PO→GRN, GRN→SI) fetch `pageSize: 100` and filter client-side. **KNOWN GAP TO FIX LATER** (acceptable at current volume)
- Date filters are not implemented on list APIs. **KNOWN GAP TO FIX LATER**
- PO created as `draft` is issued later via `PATCH .../issue` (`create` permission). UI default on blank create remains `draft`. **CLOSED**
- Payable detail has no GET-by-id; UI searches the first 100 list rows. **KNOWN GAP TO FIX LATER**
- Vendor create does not write `audit_logs`. **KNOWN GAP TO FIX LATER**

### O2C

- Sales invoices require a delivered delivery; SO-only / customer-only in the Angular form is rejected. **DELIBERATE SCOPE DECISION**
- Subscribed Plan is the UI name for `o2c_quotations`; JSON field names stay. **DELIBERATE SCOPE DECISION**
- `billing_cycle` stored, no recurring invoice generation; one invoice per plan. **DELIBERATE SCOPE DECISION** (recurring = later phase)
- `deposit_amount` does not flow into the sales invoice (same as booking `security_paid`). Refund/adjustment later. **DELIBERATE SCOPE DECISION**
- GSTIN optional on rental customer form; column remains. **DELIBERATE SCOPE DECISION**
- Collections do not post to `finance_transactions`. **DELIBERATE SCOPE DECISION**
- Draft subscribed plans are accepted/rejected via `PATCH .../accept` and `.../reject` (`approve` permission). **CLOSED**
- Customer/plan creates are not audited. **KNOWN GAP TO FIX LATER**
- Customer list API has no `search` param. Deliveries/sales-invoices/collections list APIs have no `status`/`search`. **KNOWN GAP TO FIX LATER**
- Same 100-row create-dropdown ceiling (SO→Delivery, Delivery→SI). **KNOWN GAP TO FIX LATER**

### Finance

- Cash in hand = collections + legacy receipts − expenses − P2P payments. No opening bank balance — figures can look low/negative for a business with pre-existing cash. **KNOWN GAP TO FIX LATER** (formula itself is **DELIBERATE SCOPE DECISION**)
- Single implicit “Operating cash” account; Accounts page read-only; `finance_accounts.balance` unused. No multi-account/transfers. **DELIBERATE SCOPE DECISION**
- Expense GST/category/SKU not stored; form only shows persisted fields. Do not restore expense-by-category chart until category is a real column. **DELIBERATE SCOPE DECISION**
- Income is cash-basis derived; no manual income form. **DELIBERATE SCOPE DECISION**
- Transactions list is expense debits only. **DELIBERATE SCOPE DECISION**
- GST: flat `gst_amount`, no CGST/SGST/IGST, no tax engine; expense GST reported 0. **DELIBERATE SCOPE DECISION**
- Reconciliation: no bank feed; note only. **DELIBERATE SCOPE DECISION**
- Legacy bookings stay parallel to O2C; `plan_skg` has no API. **DELIBERATE SCOPE DECISION**

### Master Data / catalog

- Split RBAC: party/reference = ADMIN/MANAGER; catalog = `create` (includes OPERATOR/FINANCE). **DELIBERATE SCOPE DECISION**
- Catalog updates 501-via-toast (no PUT). **DELIBERATE SCOPE DECISION**
- BYTEA document storage, 10 MB, PNG/JPEG/PDF only. **DELIBERATE SCOPE DECISION** (object storage later if volume grows)

### Admin / platform

- `audit_logs` append-only via trigger, not REVOKE (app role owns the table). **DELIBERATE SCOPE DECISION**
- Audit GET is `view` (all roles), not `admin`. **DELIBERATE SCOPE DECISION** (current code)
- JWT `secret_key` and DB URL have **dev defaults** in `config.py` — must override in production. **KNOWN GAP TO FIX LATER** (ops)
- Demo users seeded in bootstrap with public passwords. **KNOWN GAP TO FIX LATER** (ops)
- No `pg_dump`/backup runbook; no Alembic migrations in use. **KNOWN GAP TO FIX LATER**
- CORS is an exact `CORS_ORIGINS` allow-list (local default `http://localhost:4200`; production is the pinned frontend origin). There is **no** `*.vercel.app` regex. **DELIBERATE SCOPE DECISION**

### Reports / dashboard

- Live report set is the seven keys above; unknown keys return an empty stub, not 404. Former index cards (expense/income/audit/vendor/customer/product/invoice/receipt reports) are **not** in the live set. **DELIBERATE SCOPE DECISION**
- P&L report is cash-basis, same as dashboard net cash — not statutory. **DELIBERATE SCOPE DECISION**
- Dashboard recent expenses/invoices/receipts and the Expense vs Income trend are **live** tenant-scoped queries. Product summary stays **hidden** (seed endpoint still exists, unused by UI). Cards + cash position are live. **DELIBERATE** for the hidden product section until product-level revenue exists.

### Cross-cutting

- Almost no record Update except: users, org settings, recon note. **DELIBERATE SCOPE DECISION**
- `export` / `delete` permissions unused on APIs. **KNOWN GAP TO FIX LATER** if those features are wanted
- List date filtering missing across operational lists. **KNOWN GAP TO FIX LATER**

---

## 6. Not yet implemented

Literal list. Anything here has **zero live backend**, **seed/dummy responses**, or a **dead client path**. Do not treat these as working product.

### Seed / dummy still served if called (backend 200 with fake rows)

These endpoints still exist as scaffolding. Angular **does not call them**.

1. `GET /dashboard/products` — Product financial summary (**UI hidden**)
2. `GET /dashboard/product/{id}` — same seed list (**unused**)
3. `GET /dashboard/categories` — seed category breakdown (**not shown**; chart removed — do not restore)

Implementation: `backend/app/services/dev_seed.py` via `backend/app/api/v1/dashboard.py`.

Live dashboard (not seed): `GET /dashboard/expenses` (last 8 `finance_transactions` expense debits), `GET /dashboard/invoices` (last 8 O2C + legacy invoices), `GET /dashboard/receipts` (last 8 collections + legacy receipts), `GET /dashboard/income` (cash-basis trend: collections + receipts vs expense debits + P2P payments, bucketed daily/weekly/monthly). Expense `category` is always `"—"` because `finance_transactions` has no category column.

### Zero backend

5. **Forgot password** — page + fake toast; no `/auth/forgot-password` (or email) route
6. **Recurring invoicing** from `billing_cycle`
7. **Opening cash / bank balance**
8. **Tax calculation engine** (CGST/SGST/IGST, auto-apply GST to totals)
9. **Bank feed / statement matching** (reconciliation is a note)
10. **Object storage** for documents (BYTEA only)
11. **Business-record DELETE** (any entity)
12. **Record UPDATE** for master data and workflow documents (except users, org settings, recon note). PR PUT is the only explicit **HTTP 501**
13. **Payable GET by id**
14. **Category / subcategory / offering GET by id**
15. **`plan_skg` API** (legacy plans)
16. **Multi-account GL**, transfers, account picker
17. **Manual income posting**
18. **Merge of P2P payments / O2C collections into `finance_transactions`** (intentionally not done)
19. **Report keys** outside the seven live ones — stub empty body
20. **Date query params** on operational list APIs (audit and GST summary already have date filters)
21. **Server-side eligible-source lists** for create dropdowns (100-row client filter)

### Client leftovers (not driving live pages while `useDevSeed` is false)

22. `frontend/src/core/seed/dev-seed.ts` — `DEV_LOGIN` + `DASHBOARD_SEED` used only if `useDevSeed` is true
23. `P2pStore` + `p2p.seed.ts`, `O2cStore` + `o2c.seed.ts` (includes dummy customers/plans/offerings), `FinanceStore` + `finance.seed.ts`, `AdminStore` + `admin.seed.ts` — localStorage. Live list pages use HTTP APIs. `O2cApiService.offerings()` / `plans()` still read the O2C store; booking UI uses live `/offerings` instead
24. `frontend/.../report.service.ts` — unused localStorage report builder (live views hit `/reports/{key}`)

---

*Generated from code on 28 Aug 2026. Update this file when endpoints or gates change; do not treat `DECISIONS.md` as the inventory.*
