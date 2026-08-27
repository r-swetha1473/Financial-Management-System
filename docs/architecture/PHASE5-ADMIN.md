# Phase 5 — Users, roles, organization, and audit

Official ERD/PDF is still not in the repo. This phase uses existing tables from Phase 1:

- `organizations`, `users`, `user_sessions`
- `reference_data`
- `audit_logs`

Python/FastAPI is still unavailable. The frontend uses API contracts with organization-scoped seed stores (`bfms_admin_${orgId}`, `bfms_audit_${orgId}`). Passwords in the demo store are plaintext so login can be tested; a real backend must store only `password_hash`.

---

## A. What this phase covers

| Area | Route | Source |
|------|--------|--------|
| Users & roles | `/admin/users` | `users` |
| Reference data | `/admin/reference-data` | `reference_data` |
| Audit logs | `/admin/audit-logs` | `audit_logs` (unified org log) |
| Settings | `/admin/settings` | `organizations` |
| Documents | `/admin/documents` | Already shipped in Phase 4 |

RBAC roles match the schema check constraint: **ADMIN**, **MANAGER**, **FINANCE**, **OPERATOR**, **VIEWER**.

---

## B. Rules that are not invented

- **Roles** are the five values already in `users.role`. No extra roles, no per-screen permission matrix beyond existing `hasPermission`.
- **Settings** are organization `name`, `slug`, and `is_active`. Timezone, multi-currency, invoice templates, and branding are not in the schema.
- **Reference data** is a generic lookup (`data_type`, `code`, `label`, `is_active`). It is **not** wired to invent CGST/SGST/IGST splits or additional receipt payment modes. Cash / Card / UPI remain the only receipt modes.
- **Audit** stores action, entity, id, and a human-readable details string. The UI does not invent JSON before/after snapshots (`old_values` / `new_values` stay backend fields).
- **Automation** (schedulers, auto-post of P2P payments or O2C collections to `finance_transactions`, auto-reconciliation) is **not implemented**. Those rules are not in the schema. Settings shows a read-only note only.
- **Passwords** are never shown in lists or edit forms. Create requires a password; edit may reset it. Frontend demo storage is not a substitute for hashing.

---

## C. Access

| Screen | Who can open | Who can edit |
|--------|----------------|--------------|
| Users & Roles | ADMIN | ADMIN |
| Settings | ADMIN | ADMIN |
| Reference Data | ADMIN, MANAGER | ADMIN, MANAGER |
| Audit Logs | Any authenticated role | Read-only |
| Documents | Any authenticated role | Roles with `create` |

The last **active ADMIN** in an organization cannot be deactivated or demoted. A user cannot deactivate their own account.

Sidebar Administration items are hidden when the current role cannot open them. Route guards redirect to `/dashboard`.

---

## D. Demo users (same tenant)

Organization: **Demo Business Co.** (`org-demo-001`, slug `demo-business`)

| Email | Password | Role |
|-------|----------|------|
| admin@demo-business.com | admin123 | ADMIN |
| manager@demo-business.com | manager123 | MANAGER |
| finance@demo-business.com | finance123 | FINANCE |
| operator@demo-business.com | operator123 | OPERATOR |
| viewer@demo-business.com | viewer123 | VIEWER |

Login prefers the admin store so a password change in Users takes effect. Seed login still matches the existing admin account if the store has not been created yet.

---

## E. Unified audit

P2P, O2C, finance, and admin writes append to `bfms_audit_${orgId}`. The Audit Logs screen and the Audit report both read that store.

Finance-store `auditEntries` remain in seed data for migration into the unified log on first load. New finance writes go to the unified log only.

---

## F. API contracts

```
/api/v1/users
/api/v1/users/{id}
/api/v1/reference-data
/api/v1/reference-data/{id}
/api/v1/audit-logs
/api/v1/organizations/current
```

`GET /organizations/current` already exists from Phase 1. Phase 5 adds `PUT` for name / slug / is_active.

---

## G. What remains after this phase

- FastAPI persistence, password hashing, and session revocation
- Real `audit_logs.old_values` / `new_values` from the database
- Object storage for documents
- Any automation engine (out of scope until product rules exist)
