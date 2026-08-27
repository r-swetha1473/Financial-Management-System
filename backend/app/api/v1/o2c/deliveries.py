"""O2C delivery endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.delivery import DeliveryCreate, DeliveryOut
from app.services import delivery_service

router = APIRouter(prefix="/deliveries", tags=["O2C Deliveries"])


@router.get("", response_model=PaginatedResponse[DeliveryOut])
async def list_deliveries(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[DeliveryOut]:
    items, total = await delivery_service.list_deliveries(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{delivery_id}", response_model=ApiResponse[DeliveryOut])
async def get_delivery(
    delivery_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DeliveryOut]:
    record = await delivery_service.get_delivery(session, current.tenant_id, delivery_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[DeliveryOut], status_code=201)
async def create_delivery(
    payload: DeliveryCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DeliveryOut]:
    record = await delivery_service.create_delivery(session, current.tenant_id, payload)
    return ApiResponse(data=record)
