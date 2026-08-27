-- Username uniqueness per organization (case-insensitive), matching Angular admin store.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_organization_id_lower_username_uidx
    ON users (organization_id, lower(username));

INSERT INTO schema_migrations (filename)
VALUES ('008_users_username_unique.sql')
ON CONFLICT (filename) DO NOTHING;
