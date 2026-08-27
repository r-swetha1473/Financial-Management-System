"""Audit-log read service. Append-only; no mutations."""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.audit_log import AuditLogOut


def _to_out(row: AuditLog, email: str | None, full_name: str | None) -> AuditLogOut:
    return AuditLogOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        user_id=str(row.user_id) if row.user_id else None,
        user_email=email or "",
        user_name=full_name or "",
        action=row.action,
        entity_name=row.entity_name,
        entity_id=str(row.entity_id) if row.entity_id else None,
        old_values=row.old_values,
        new_values=row.new_values,
        created_at=row.created_at,
    )


async def list_audit_logs(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    *,
    entity_name: str | None = None,
    action: str | None = None,
    actor_user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[AuditLogOut], int]:
    rows, total = await AuditLogRepository(session, tenant_id).list_page(
        page,
        page_size,
        entity_name=entity_name,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return [_to_out(row, email, name) for row, email, name in rows], total
