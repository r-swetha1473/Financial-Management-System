"""Audit-log persistence. Tenant-scoped list with optional AND filters."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(AuditLog.organization_id, self.tenant_id)

    def _with_actor(self):
        return (
            select(AuditLog, User.email, User.full_name)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(self._tenant_filter())
        )

    def _filters(
        self,
        *,
        entity_name: str | None,
        action: str | None,
        actor_user_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ):
        clauses = []
        if entity_name:
            clauses.append(AuditLog.entity_name == entity_name)
        if action:
            clauses.append(AuditLog.action == action)
        if actor_user_id is not None:
            clauses.append(AuditLog.user_id == actor_user_id)
        if date_from is not None:
            start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
            clauses.append(AuditLog.created_at >= start)
        if date_to is not None:
            end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
            clauses.append(AuditLog.created_at < end)
        return clauses

    async def list_page(
        self,
        page: int,
        page_size: int,
        *,
        entity_name: str | None = None,
        action: str | None = None,
        actor_user_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[tuple[AuditLog, str | None, str | None]], int]:
        extra = self._filters(
            entity_name=entity_name,
            action=action,
            actor_user_id=actor_user_id,
            date_from=date_from,
            date_to=date_to,
        )
        count_stmt = select(func.count()).select_from(AuditLog).where(self._tenant_filter(), *extra)
        total = await self.session.scalar(count_stmt) or 0
        stmt = self._with_actor()
        if extra:
            stmt = stmt.where(and_(*extra))
        stmt = (
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)
