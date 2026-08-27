"""Purchase-order application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase_order import PurchaseOrder
from app.models.vendor import Vendor
from app.repositories.purchase_orders import PurchaseOrderRepository
from app.repositories.purchase_requests import PurchaseRequestRepository
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderOut

_APPROVED = "approved"


def _to_out(row: PurchaseOrder, vendor_name: str | None, request_number: str | None) -> PurchaseOrderOut:
    return PurchaseOrderOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        purchase_request_id=str(row.purchase_request_id) if row.purchase_request_id else None,
        purchase_request_number=request_number or "",
        vendor_id=str(row.vendor_id),
        vendor_name=vendor_name or "",
        po_number=row.po_number,
        status=row.status,
        order_date=row.order_date,
        total_amount=row.total_amount,
        created_at=row.created_at,
    )


async def list_purchase_orders(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[PurchaseOrderOut], int]:
    rows, total = await PurchaseOrderRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(order, vendor_name, request_number) for order, vendor_name, request_number in rows], total


async def get_purchase_order(session: AsyncSession, tenant_id: UUID, order_id: UUID) -> PurchaseOrderOut:
    named = await PurchaseOrderRepository(session, tenant_id).get_by_id(order_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found in this organization.",
        )
    order, vendor_name, request_number = named
    return _to_out(order, vendor_name, request_number)


async def create_purchase_order(
    session: AsyncSession,
    tenant_id: UUID,
    payload: PurchaseOrderCreate,
) -> PurchaseOrderOut:
    source = None
    if payload.purchase_request_id is not None:
        source = await PurchaseRequestRepository(session, tenant_id).get_for_update(payload.purchase_request_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase request not found in this organization.",
            )
        if source.status != _APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase request must be approved before converting to a purchase order.",
            )

    vendor_id = payload.vendor_id or (source.vendor_id if source is not None else None)
    if vendor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A vendor is required to create a purchase order.",
        )
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None or vendor.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found in this organization.",
        )
    if source is not None and source.vendor_id is not None and source.vendor_id != vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor does not match the purchase request.",
        )

    order = await PurchaseOrderRepository(session, tenant_id).create(
        vendor_id=vendor_id,
        purchase_request=source,
        order_date=payload.order_date or date.today(),
        total_amount=payload.total_amount if payload.total_amount is not None else Decimal("0"),
        status=payload.status,
    )
    return _to_out(order, vendor.name, source.request_number if source is not None else None)
