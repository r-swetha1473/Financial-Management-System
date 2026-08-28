"""P2P purchase-order endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderOut, PurchaseOrderStatus
from app.services import purchase_order_service

router = APIRouter(prefix="/purchase-orders", tags=["P2P Purchase Orders"])


@router.get("", response_model=PaginatedResponse[PurchaseOrderOut])
async def list_purchase_orders(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    vendor_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[PurchaseOrderStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[PurchaseOrderOut]:
    items, total = await purchase_order_service.list_purchase_orders(
        session,
        current.tenant_id,
        page,
        page_size,
        vendor_id=vendor_id,
        status=status,
        search=search,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{order_id}", response_model=ApiResponse[PurchaseOrderOut])
async def get_purchase_order(
    order_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseOrderOut]:
    record = await purchase_order_service.get_purchase_order(session, current.tenant_id, order_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[PurchaseOrderOut], status_code=201)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseOrderOut]:
    record = await purchase_order_service.create_purchase_order(session, current.tenant_id, payload)
    return ApiResponse(data=record)


@router.patch("/{order_id}/issue", response_model=ApiResponse[PurchaseOrderOut])
async def issue_purchase_order(
    order_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseOrderOut]:
    record = await purchase_order_service.issue_purchase_order(
        session, current.tenant_id, current.user_id, order_id
    )
    return ApiResponse(data=record)
