"""Legacy booking / invoice_skg / receipt endpoints. Tables already existed."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.paging import paginated
from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.legacy_booking import (
    BookingCreate,
    BookingOut,
    LegacyInvoiceCreate,
    LegacyInvoiceOut,
    ReceiptCreate,
    ReceiptOut,
)
from app.services import legacy_booking_service

bookings_router = APIRouter(prefix="/bookings", tags=["Bookings"])
invoices_router = APIRouter(prefix="/invoices", tags=["Booking Invoices"])
receipts_router = APIRouter(prefix="/receipts", tags=["Receipts"])


@bookings_router.get("", response_model=PaginatedResponse[BookingOut])
async def list_bookings(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    customer_id: UUID | None = None,
):
    items, total = await legacy_booking_service.list_bookings(
        session, current.tenant_id, page, page_size, customer_id
    )
    return paginated(items, total, page, page_size)


@bookings_router.get("/{booking_id}", response_model=ApiResponse[BookingOut])
async def get_booking(
    booking_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await legacy_booking_service.get_booking(session, current.tenant_id, booking_id))


@bookings_router.post("", response_model=ApiResponse[BookingOut], status_code=201)
async def create_booking(
    payload: BookingCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await legacy_booking_service.create_booking(session, current.tenant_id, payload))


@invoices_router.get("", response_model=PaginatedResponse[LegacyInvoiceOut])
async def list_invoices(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    customer_id: UUID | None = None,
):
    items, total = await legacy_booking_service.list_invoices(
        session, current.tenant_id, page, page_size, customer_id
    )
    return paginated(items, total, page, page_size)


@invoices_router.get("/{invoice_id}", response_model=ApiResponse[LegacyInvoiceOut])
async def get_invoice(
    invoice_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await legacy_booking_service.get_invoice(session, current.tenant_id, invoice_id))


@invoices_router.post("", response_model=ApiResponse[LegacyInvoiceOut], status_code=201)
async def create_invoice(
    payload: LegacyInvoiceCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await legacy_booking_service.create_invoice(session, current.tenant_id, payload))


@receipts_router.get("", response_model=PaginatedResponse[ReceiptOut])
async def list_receipts(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await legacy_booking_service.list_receipts(session, current.tenant_id, page, page_size)
    return paginated(items, total, page, page_size)


@receipts_router.get("/{receipt_id}", response_model=ApiResponse[ReceiptOut])
async def get_receipt(
    receipt_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await legacy_booking_service.get_receipt(session, current.tenant_id, receipt_id))


@receipts_router.post("", response_model=ApiResponse[ReceiptOut], status_code=201)
async def create_receipt(
    payload: ReceiptCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(
        data=await legacy_booking_service.create_receipt(session, current.tenant_id, current.user_id, payload)
    )
