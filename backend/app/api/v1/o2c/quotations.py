"""O2C quotation endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.quotation import QuotationCreate, QuotationOut, QuotationStatus
from app.services import quotation_service

router = APIRouter(prefix="/quotations", tags=["O2C Subscribed Plans"])


@router.get("", response_model=PaginatedResponse[QuotationOut])
async def list_quotations(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    customer_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[QuotationStatus | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[QuotationOut]:
    items, total = await quotation_service.list_quotations(
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


@router.get("/{quotation_id}", response_model=ApiResponse[QuotationOut])
async def get_quotation(
    quotation_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[QuotationOut]:
    record = await quotation_service.get_quotation(session, current.tenant_id, quotation_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[QuotationOut], status_code=201)
async def create_quotation(
    payload: QuotationCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[QuotationOut]:
    record = await quotation_service.create_quotation(session, current.tenant_id, payload)
    return ApiResponse(data=record)


@router.patch("/{quotation_id}/accept", response_model=ApiResponse[QuotationOut])
async def accept_quotation(
    quotation_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[QuotationOut]:
    record = await quotation_service.decide_quotation(
        session, current.tenant_id, current.user_id, quotation_id, "accepted"
    )
    return ApiResponse(data=record)


@router.patch("/{quotation_id}/reject", response_model=ApiResponse[QuotationOut])
async def reject_quotation(
    quotation_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[QuotationOut]:
    record = await quotation_service.decide_quotation(
        session, current.tenant_id, current.user_id, quotation_id, "rejected"
    )
    return ApiResponse(data=record)
