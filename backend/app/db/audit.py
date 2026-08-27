"""Insert audit_logs rows in the caller's transaction. Do not commit here."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def write_audit_log(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID | None,
    action: str,
    entity_name: str,
    entity_id: UUID | None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
    )
    session.add(entry)
    return entry
