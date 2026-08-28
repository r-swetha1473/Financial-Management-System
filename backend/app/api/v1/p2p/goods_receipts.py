"""P2P goods-receipt endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.goods_receipt import GoodsReceiptCreate, GoodsReceiptOut, GoodsReceiptStatus
from app.services import goods_receipt_service

router = APIRouter(prefix="/goods-receipts", tags=["P2P Goods Receipts"])


@router.get("", response_model=PaginatedResponse[GoodsReceiptOut])
async def list_goods_receipts(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[GoodsReceiptStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[GoodsReceiptOut]:
    items, total = await goods_receipt_service.list_goods_receipts(
        session, current.tenant_id, page, page_size, status=status, search=search
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{receipt_id}", response_model=ApiResponse[GoodsReceiptOut])
async def get_goods_receipt(
    receipt_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[GoodsReceiptOut]:
    record = await goods_receipt_service.get_goods_receipt(session, current.tenant_id, receipt_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[GoodsReceiptOut], status_code=201)
async def create_goods_receipt(
    payload: GoodsReceiptCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[GoodsReceiptOut]:
    record = await goods_receipt_service.create_goods_receipt(session, current.tenant_id, payload)
    return ApiResponse(data=record)
