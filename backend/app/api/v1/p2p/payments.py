"""P2P supplier-payment endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["P2P Payments"])


@router.get("", response_model=PaginatedResponse[PaymentOut])
async def list_payments(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[PaymentOut]:
    items, total = await payment_service.list_payments(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{payment_id}", response_model=ApiResponse[PaymentOut])
async def get_payment(
    payment_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PaymentOut]:
    record = await payment_service.get_payment(session, current.tenant_id, payment_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[PaymentOut], status_code=201)
async def create_payment(
    payload: PaymentCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PaymentOut]:
    record = await payment_service.create_payment(session, current.tenant_id, current.user_id, payload)
    return ApiResponse(data=record)
