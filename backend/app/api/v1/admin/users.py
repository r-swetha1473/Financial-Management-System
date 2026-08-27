"""Admin user endpoints. Last-admin and self-deactivation are enforced with row locks."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.admin_user import UserCreate, UserOut, UserUpdate
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services import admin_user_service

router = APIRouter(prefix="/users", tags=["Admin Users"])


@router.get("", response_model=PaginatedResponse[UserOut])
async def list_users(
    current: Annotated[CurrentUser, Depends(require_permission("admin"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str = "",
    status: str = "",
    role: str = "",
) -> PaginatedResponse[UserOut]:
    items, total = await admin_user_service.list_users(
        session,
        current.tenant_id,
        page,
        page_size,
        search=search,
        status_filter=status,
        role=role,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.post("", response_model=ApiResponse[UserOut], status_code=201)
async def create_user(
    payload: UserCreate,
    current: Annotated[CurrentUser, Depends(require_permission("admin"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[UserOut]:
    record = await admin_user_service.create_user(session, current.tenant_id, current.user_id, payload)
    return ApiResponse(data=record)


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    current: Annotated[CurrentUser, Depends(require_permission("admin"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[UserOut]:
    record = await admin_user_service.update_user(
        session, current.tenant_id, current.user_id, user_id, payload
    )
    return ApiResponse(data=record)
