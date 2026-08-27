# Phase 2 — P2P architecture

Official ERD/PDF is still not in the repo. Validation is against:
- Specified existing entities (`vendors`, `expenses`, …)
- Additive P2P tables in `backend/db/init/001_schema.sql` (Phase 1)

P2P document tables are **not** in the original entity list. They are additive. Existing names are not renamed. No line-item, 3-way-match, or CGST/SGST/IGST rules are invented.

Python/FastAPI is not on PATH. Phase 2 ships as **frontend + API contracts + org-scoped seed store**. Real persistence, locking, and audit require the backend.

---

## A. P2P workflow

Header-level documents only (matches current tables):

```
Vendor (master)
  → Purchase Request     (optional vendor)
  → Purchase Order       (required vendor, optional request)
  → Goods/Service Receipt (required purchase order)
  → Supplier Invoice     (required vendor; optional PO and GRN)
  → Payment              (required supplier invoice)
  → Payables             (financial outstanding for that invoice)
```

Approval is a **status on the supplier invoice** (`approvalStatus`), not a separate document.

Not implemented (unsupported / not in schema):
- Purchase/invoice line items
- Automatic 3-way quantity matching
- GST component split (CGST/SGST/IGST)
- Posting to a general ledger
- Linking `expenses.purchase_order_number` as a hard FK

UI shows related documents so a user can walk Vendor → PR → PO → GRN → Invoice → Payment. The UI does not block a later document unless the schema requires the FK (GRN needs a PO; payment needs an invoice).

---

## B. P2P screens / routes

| Screen | Route | Actions |
|--------|--------|---------|
| P2P overview | `/p2p` | Process map |
| Vendors list | `/master/vendors` | Search, filter, pagination, create/edit modal, view |
| Vendor detail | `/master/vendors/:id` | Overview, contact, GST, related P2P docs |
| Purchase requests | `/p2p/purchase-requests` | List + modal |
| PR detail | `/p2p/purchase-requests/:id` | View + create PO |
| Purchase orders | `/p2p/purchase-orders` | List + modal |
| PO detail | `/p2p/purchase-orders/:id` | View + create GRN |
| Receipts | `/p2p/receipts` | List + modal |
| GRN detail | `/p2p/receipts/:id` | View + create supplier invoice |
| Supplier invoices | `/p2p/supplier-invoices` | List + modal |
| Invoice detail | `/p2p/supplier-invoices/:id` | View + record payment |
| Payments | `/p2p/payments` | List + modal (confirm before save) |
| Payment detail | `/p2p/payments/:id` | View |
| Payables | `/p2p/payables` | List (read-focused) |
| Payable detail | `/p2p/payables/:id` | View + links |

---

## C. Entities and relationships

All rows are scoped by `organization_id`.

```
organizations 1──* vendors
vendors 1──* p2p_purchase_requests (optional)
vendors 1──* p2p_purchase_orders
p2p_purchase_requests 1──* p2p_purchase_orders (optional)
p2p_purchase_orders 1──* p2p_goods_receipts
vendors 1──* p2p_supplier_invoices
p2p_purchase_orders 1──* p2p_supplier_invoices (optional)
p2p_goods_receipts 1──* p2p_supplier_invoices (optional)
p2p_supplier_invoices 1──* p2p_payments
p2p_supplier_invoices 1──* payables (source_type + source_id)
```

`invoice.amount` is the amount used for payables/payments. `gst_amount` is displayed only — it is not added in the UI (inclusive vs exclusive is not defined).

---

## D. Required database changes

**No new tables in Phase 2.** Use the Phase 1 P2P tables.

Gaps to confirm later (not applied now):
- Line-item tables
- Notes on PO / GRN / payment
- `due_date` on supplier invoice (exists on `payables` only)
- FK from `expenses.purchase_order_number` to `p2p_purchase_orders`

---

## E. API endpoints

```
/api/v1/vendors
/api/v1/p2p/purchase-requests
/api/v1/p2p/purchase-orders
/api/v1/p2p/goods-receipts
/api/v1/p2p/supplier-invoices
/api/v1/p2p/payments
/api/v1/p2p/payables
```

Each collection: `GET` (filter + page), `POST`, `GET /{id}`, `PUT /{id}`.  
Payables: `GET`, `GET /{id}` (created with the invoice, not a free-form ledger).  
Payment `POST` must be transactional on the backend (lock invoice, sum payments, validate outstanding, insert, update payable, audit, commit).

---

## F. Status definitions

| Document | Statuses |
|----------|----------|
| Vendor | `active`, `inactive` |
| Purchase request | `draft`, `submitted`, `approved`, `rejected`, `converted` |
| Purchase order | `draft`, `issued`, `received`, `closed`, `cancelled` |
| Goods/service receipt | `received`, `cancelled` |
| Supplier invoice | `pending`, `partially_paid`, `paid`, `cancelled` |
| Invoice approval | `pending`, `approved`, `rejected` |
| Payment | `completed`, `cancelled` |
| Payable | `open`, `partial`, `closed` |

These are document states for the UI. They are not a full accounting policy.

---

## G. UI-only vs backend-required

| Capability | Phase 2 now | Backend required |
|------------|-------------|------------------|
| Lists, search, filters, pagination, detail, forms | Frontend (seed fallback) | Tenant-filtered SQL |
| Cross-document navigation | Frontend | Same IDs from API |
| Payment not exceeding outstanding | Frontend check | **Must re-validate in a transaction** |
| Payable outstanding update | Simulated in seed store | **Must be transactional** |
| Approval / RBAC | Buttons hidden by role | **Must enforce 403** |
| Multi-org isolation | Session `organizationId` on seed key | **Must filter every query** |
| Audit log of P2P changes | Not written | `audit_logs` insert |
| Document PDF upload | Not in Phase 2 | `documents` + storage |

Demo login still works without Python. Writes go to `localStorage` keyed by organization until FastAPI is available.
