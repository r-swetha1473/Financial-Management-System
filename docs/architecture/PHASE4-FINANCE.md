# Phase 4 — Finance, GST, documents, and reports

Official ERD/PDF is still not in the repo. This phase uses existing tables from Phase 1:

- `expenses`, `income_offering`, `products`, `categories`, `subcategories`
- `finance_accounts`, `finance_transactions`
- `documents`
- GST amounts already stored on `expenses`, `invoice_skg`, `o2c_sales_invoices`, `p2p_supplier_invoices`

No general ledger, no invoice line items, no CGST/SGST/IGST split columns. Python/FastAPI is still unavailable; the frontend uses API contracts with an organization-scoped seed store (`bfms_finance_${orgId}`).

---

## A. What this phase covers

| Area | Route | Source |
|------|--------|--------|
| Products | `/master/products` | `products` |
| Categories | `/master/categories` | `categories`, `subcategories` |
| Services / offerings | `/master/services` | `income_offering` |
| Expenses | `/finance/expenses` | `expenses` (operational spend, not a P2P document) |
| Income | `/finance/income` | Derived from invoices, receipts, O2C invoices, collections |
| Accounts | `/finance/accounts` | `finance_accounts` |
| Transactions | `/finance/transactions` | `finance_transactions` |
| GST / Tax | `/finance/gst` | Sum of stored GST amounts |
| Reconciliation | `/finance/reconciliation` | Match book transactions (no statement-import table) |
| Documents | `/admin/documents` | Metadata only (`storage_key`, file name/size/type) |
| Reports | `/reports/*` | Read-only aggregates of the above + P2P/O2C stores |

Bookings, existing invoices, and receipts stay as implemented in Phase 3.

---

## B. Rules that are not invented

- **GST:** `gst_amount` / `gst_percentage` / `is_gst_invoice` are displayed and summed. They are **not** added to invoice or expense cost in the UI. CGST/SGST/IGST are **not** split (columns do not exist).
- **Income:** There is no `income` transaction table. The income screen lists existing sales documents. Accrual (invoice) and cash (receipt/collection) are labelled separately.
- **P2P payments / O2C collections** do not auto-post to `finance_transactions`. Cash movement on accounts is recorded only when a finance transaction is saved. Cash-flow reports show both posted transactions and unposted collections/payments.
- **Services** are `income_offering` rows, not a new table.
- **Reconciliation** marks `finance_transactions.reconciled`. Bank statement import is not in the schema.
- **Documents** store metadata (and optional `storage_key`). No public file URLs.

---

## C. Accounts and transactions

`account_type`: `bank` | `cash`.

Transaction types follow **bank-statement convention** (documented, not a full GL):

- `credit` — money in — increases account balance
- `debit` — money out — decreases account balance

Opening balance is set when the account is created. Later balance changes go through transactions. Editing a transaction reverses the previous effect, then applies the new one.

Additive schema field: `finance_transactions.reconciled` (boolean, default false).

---

## D. Expense fields (existing table)

Vendor, category, subcategory, product, product/service name, SKU, quantity, unit price, cost, GST %, GST amount, purchase order number (text, not a hard FK), date, entered by, status (`pending` / `approved` / `rejected`).

`purchase_order_number` may match a P2P PO number for navigation; it is not enforced as an FK.

---

## E. API contracts

```
/api/v1/products
/api/v1/categories
/api/v1/subcategories
/api/v1/offerings
/api/v1/expenses
/api/v1/income
/api/v1/finance/accounts
/api/v1/finance/transactions
/api/v1/finance/gst
/api/v1/documents
/api/v1/reports/{key}
```

---

## F. Reports (read-only)

P2P, O2C, expenses, income/sales, payables, receivables, GST summary, cash flow, financial summary, audit, vendor expense, customer income, product summary, invoices, receipts.

CSV download is client-side from the displayed rows (`export` permission). PDF remains backend-later.

Audit rows in this phase are written for finance-store changes and are migrated into the unified `audit_logs` UI in Phase 5.

---

## G. UI vs backend

| Now | Backend required |
|-----|------------------|
| Org-scoped lists/forms | Tenant SQL |
| Transaction balance adjust in local store | Single DB transaction + row lock |
| GST totals from stored amounts | Same sums in SQL |
| Document metadata | Authenticated upload to object storage |
| CSV of current table | Server export / PDF |
