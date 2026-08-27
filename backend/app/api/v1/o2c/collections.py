"""O2C collection endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.collection import CollectionCreate, CollectionOut
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services import collection_service

router = APIRouter(prefix="/collections", tags=["O2C Collections"])


@router.get("", response_model=PaginatedResponse[CollectionOut])
async def list_collections(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[CollectionOut]:
    items, total = await collection_service.list_collections(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{collection_id}", response_model=ApiResponse[CollectionOut])
async def get_collection(
    collection_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CollectionOut]:
    record = await collection_service.get_collection(session, current.tenant_id, collection_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[CollectionOut], status_code=201)
async def create_collection(
    payload: CollectionCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CollectionOut]:
    record = await collection_service.create_collection(
        session, current.tenant_id, current.user_id, payload
    )
    return ApiResponse(data=record)
