-- Append-only audit_logs. The app role owns this table, so REVOKE UPDATE/DELETE
-- does not bind the owner; a BEFORE trigger is the actual enforcement.
-- Test teardown may SET LOCAL app.allow_audit_delete = on (transaction-scoped)
-- so isolation orgs can be deleted. Application request handlers never set this.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION audit_logs_block_mutate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('app.allow_audit_delete', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'audit_logs is append-only'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;
CREATE TRIGGER audit_logs_append_only
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION audit_logs_block_mutate();

REVOKE UPDATE, DELETE ON TABLE audit_logs FROM PUBLIC;

CREATE INDEX IF NOT EXISTS audit_logs_org_created_at_idx
    ON audit_logs (organization_id, created_at DESC);

INSERT INTO schema_migrations (filename)
VALUES ('009_audit_logs_append_only.sql')
ON CONFLICT (filename) DO NOTHING;
