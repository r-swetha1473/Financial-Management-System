"""Tenant-scoped repository base. Organization always comes from the session, never the body."""

from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.tenant import for_tenant


class TenantScopedRepository:
    """Every query must be constrained with for_tenant() on organization_id."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    def scoped(self, stmt: Select, organization_id_column: ColumnElement[UUID]) -> Select:
        return stmt.where(for_tenant(organization_id_column, self.tenant_id))
