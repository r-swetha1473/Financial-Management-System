"""O2C sales-invoice endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.sales_invoice import SalesInvoiceCreate, SalesInvoiceOut
from app.services import sales_invoice_service

router = APIRouter(prefix="/sales-invoices", tags=["O2C Sales Invoices"])


@router.get("", response_model=PaginatedResponse[SalesInvoiceOut])
async def list_sales_invoices(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[SalesInvoiceOut]:
    items, total = await sales_invoice_service.list_sales_invoices(
        session, current.tenant_id, page, page_size
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{invoice_id}", response_model=ApiResponse[SalesInvoiceOut])
async def get_sales_invoice(
    invoice_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesInvoiceOut]:
    record = await sales_invoice_service.get_sales_invoice(session, current.tenant_id, invoice_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[SalesInvoiceOut], status_code=201)
async def create_sales_invoice(
    payload: SalesInvoiceCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesInvoiceOut]:
    record = await sales_invoice_service.create_sales_invoice(session, current.tenant_id, payload)
    return ApiResponse(data=record)


@router.patch("/{invoice_id}/approve", response_model=ApiResponse[SalesInvoiceOut])
async def approve_sales_invoice(
    invoice_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesInvoiceOut]:
    record = await sales_invoice_service.decide_sales_invoice(
        session, current.tenant_id, current.user_id, invoice_id, "approved"
    )
    return ApiResponse(data=record)


@router.patch("/{invoice_id}/reject", response_model=ApiResponse[SalesInvoiceOut])
async def reject_sales_invoice(
    invoice_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[SalesInvoiceOut]:
    record = await sales_invoice_service.decide_sales_invoice(
        session, current.tenant_id, current.user_id, invoice_id, "rejected"
    )
    return ApiResponse(data=record)
