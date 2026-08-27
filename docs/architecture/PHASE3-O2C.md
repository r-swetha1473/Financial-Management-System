# Phase 3 — O2C and existing sales records

Official ERD/PDF is still not in the repo. This phase uses:
- Existing entities: `customer_skg`, `booking_skg`, `plan_skg`, `income_offering`, `invoice_skg`, `invoice_receipts`
- Additive O2C tables from Phase 1: `o2c_quotations`, `o2c_sales_orders`, `o2c_deliveries`, `o2c_sales_invoices`, `o2c_collections`, `receivables`

Existing table names are not renamed. O2C documents do **not** replace `invoice_skg` / `invoice_receipts`. Both remain, with clear UI labels.

Python/FastAPI is not on PATH. Frontend uses the same API contracts with an organization-scoped seed store.

No invented rules: no quotation line items, no automatic tax split, no merging O2C invoices with `invoice_skg`.

---

## A. O2C workflow

```
Customer (customer_skg)
  → Quotation
  → Sales Order          (required customer, optional quotation)
  → Delivery / Service   (required sales order)
  → Sales Invoice        (required customer; optional order and delivery)
  → Collection           (required sales invoice)
  → Receivables          (outstanding for that sales invoice)
```

Parallel existing records (not a second invented cycle):

```
Customer → Booking (offering, dates, security paid)
         → Invoice (invoice_skg: booking, plan, GST flag)
         → Receipt (invoice_receipts: cash/card/UPI)
```

---

## B. Screens / routes

| Screen | Route |
|--------|--------|
| O2C overview | `/o2c` |
| Customers | `/master/customers`, `/master/customers/:id` |
| Quotations | `/o2c/quotations`, `/:id` |
| Sales orders | `/o2c/sales-orders`, `/:id` |
| Deliveries | `/o2c/deliveries`, `/:id` |
| Sales invoices | `/o2c/sales-invoices`, `/:id` |
| Collections | `/o2c/collections`, `/:id` |
| Receivables | `/o2c/receivables`, `/:id` |
| Bookings | `/finance/bookings`, `/:id` |
| Invoices (`invoice_skg`) | `/finance/invoices`, `/:id` |
| Receipts | `/finance/receipts`, `/:id` |

---

## C. Relationships

All rows: `organization_id`.

O2C: customer 1—* quotations / orders / invoices / receivables; order 1—* deliveries; invoice 1—* collections.

Existing: customer 1—* bookings / invoice_skg; booking *—1 offering; invoice_skg *—1 booking/plan; invoice_skg 1—* invoice_receipts.

---

## D. Database changes

**None in Phase 3.** Use existing + Phase 1 O2C tables.

Gaps (not applied): line items; address-proof as `documents` row (UI stores metadata only); merging `invoice_skg` with `o2c_sales_invoices`.

---

## E. API

```
/api/v1/customers
/api/v1/o2c/quotations
/api/v1/o2c/sales-orders
/api/v1/o2c/deliveries
/api/v1/o2c/sales-invoices
/api/v1/o2c/collections
/api/v1/o2c/receivables
/api/v1/bookings
/api/v1/invoices
/api/v1/receipts
```

Collection and receipt POST must be transactional on the backend (lock invoice, sum paid, validate outstanding, insert, update receivable/pending, audit, commit).

---

## F. Statuses

| Document | Statuses |
|----------|----------|
| Quotation | `draft`, `sent`, `accepted`, `rejected`, `converted` |
| Sales order | `confirmed`, `fulfilled`, `cancelled` |
| Delivery | `delivered`, `cancelled` |
| Sales invoice / invoice_skg | `pending`, `partially_paid`, `paid`, `cancelled` |
| Collection / receipt | `completed`, `cancelled` |
| Receivable | `open`, `partial`, `closed` |

Booking has no status column in the ERD — none invented.

---

## G. UI-only vs backend

| Now | Backend required |
|-----|------------------|
| Lists, filters, pagination, trail, forms | Tenant SQL |
| Collection/receipt ≤ outstanding | Transactional re-check |
| UPI last-4 required in UI | Same validation server-side |
| Address-proof file metadata | Authenticated `documents` upload |
| Receivable outstanding in local store | Transaction + audit |

---

## H. Frontend implementation (this phase)

Angular screens, org-scoped `localStorage` store (`bfms_o2c_${orgId}`), and API contracts are in place. FastAPI handlers remain Phase 1 skeleton until Python is available.

O2C sales invoices and existing invoices stay on separate routes and are not merged.
