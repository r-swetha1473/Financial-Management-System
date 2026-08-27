# ERD

Place the official ERD / PDF export in this folder.

Phase 1 PostgreSQL script: `backend/db/init/001_schema.sql`

That script **preserves** specified entity names and **adds**:

- `organizations` and `organization_id` (SaaS tenancy — missing from the original entity list)
- P2P / O2C / finance tables
- `documents`

Do not apply it as a destructive rewrite of an existing production database until the official ERD is compared line by line.
