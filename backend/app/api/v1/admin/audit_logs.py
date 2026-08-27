"""Admin audit-log list. Read-only; tenant from JWT. Any signed-in role with view."""

from datetime import date
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.audit_log import AuditLogOut
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["Admin Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogOut])
async def list_audit_logs(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    entity_name: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    actor_user_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> PaginatedResponse[AuditLogOut]:
    name = (entity_name or entity_type or "").strip() or None
    act = (action or "").strip() or None
    items, total = await audit_log_service.list_audit_logs(
        session,
        current.tenant_id,
        page,
        page_size,
        entity_name=name,
        action=act,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )
