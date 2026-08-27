"""Audit log list schemas. Maps to audit_logs: old_values/new_values JSONB, entity_name (not entity_type)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.common import CamelModel


class AuditLogOut(CamelModel):
    id: str
    organization_id: str
    user_id: str | None = None
    user_email: str = ""
    user_name: str = ""
    action: str
    entity_name: str
    entity_id: str | None = None
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    created_at: datetime
