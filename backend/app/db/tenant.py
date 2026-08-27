"""Tenant filter helpers. Organization always comes from the authenticated context."""

from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement


def for_tenant(organization_id_column: ColumnElement[UUID], tenant_id: UUID) -> ColumnElement[bool]:
    return organization_id_column == tenant_id

