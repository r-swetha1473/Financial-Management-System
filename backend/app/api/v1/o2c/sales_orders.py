"""O2C sales-order endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.sales_order import SalesOrderCreate, SalesOrderOut, SalesOrderStatus
from app.services import sales_order_service

router = APIRouter(prefix="/sales-orders", tags=["O2C Sales Orders"])


@router.get("", response_model=PaginatedResponse[SalesOrderOut])
async def list_sales_orders(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    customer_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[SalesOrderStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[SalesOrderOut]:
    items, total = await sales_order_service.list_sales_orders(
        session,
        current.tenant_id,
        page,
        page_size,
        customer_id=customer_id,
        status=status,
        search=search,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{order_id}", response_model=ApiResponse[SalesOrderOut])
async def get_sales_order(
    order_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesOrderOut]:
    record = await sales_order_service.get_sales_order(session, current.tenant_id, order_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[SalesOrderOut], status_code=201)
async def create_sales_order(
    payload: SalesOrderCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesOrderOut]:
    record = await sales_order_service.create_sales_order(session, current.tenant_id, payload)
    return ApiResponse(data=record)
