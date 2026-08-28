"""Goods-receipt application service. Tenant comes from the session only."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goods_receipt import GoodsReceipt
from app.models.vendor import Vendor
from app.repositories.goods_receipts import GoodsReceiptRepository
from app.repositories.purchase_orders import PurchaseOrderRepository
from app.schemas.goods_receipt import GoodsReceiptCreate, GoodsReceiptOut

_RECEIVABLE = "issued"


def _to_out(
    row: GoodsReceipt,
    po_number: str | None,
    vendor_id: UUID | None,
    vendor_name: str | None,
) -> GoodsReceiptOut:
    return GoodsReceiptOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        purchase_order_id=str(row.purchase_order_id),
        po_number=po_number or "",
        vendor_id=str(vendor_id) if vendor_id else None,
        vendor_name=vendor_name or "",
        grn_number=row.grn_number,
        status=row.status,
        receipt_date=row.receipt_date,
        created_at=row.created_at,
    )


async def list_goods_receipts(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[GoodsReceiptOut], int]:
    rows, total = await GoodsReceiptRepository(session, tenant_id).list_page(
        page, page_size, status=status, search=search
    )
    return [
        _to_out(receipt, po_number, vendor_id, vendor_name)
        for receipt, po_number, vendor_id, vendor_name in rows
    ], total


async def get_goods_receipt(session: AsyncSession, tenant_id: UUID, receipt_id: UUID) -> GoodsReceiptOut:
    named = await GoodsReceiptRepository(session, tenant_id).get_by_id(receipt_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goods receipt not found in this organization.",
        )
    receipt, po_number, vendor_id, vendor_name = named
    return _to_out(receipt, po_number, vendor_id, vendor_name)


async def create_goods_receipt(
    session: AsyncSession,
    tenant_id: UUID,
    payload: GoodsReceiptCreate,
) -> GoodsReceiptOut:
    po_repo = PurchaseOrderRepository(session, tenant_id)
    order = await po_repo.get_for_update(payload.purchase_order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found in this organization.",
        )
    if order.status != _RECEIVABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase order must be issued before a goods receipt can be recorded.",
        )

    vendor = await session.get(Vendor, order.vendor_id)
    vendor_name = vendor.name if vendor and vendor.organization_id == tenant_id else None

    receipt = await GoodsReceiptRepository(session, tenant_id).create_against_issued_order(
        purchase_order=order,
        receipt_date=payload.receipt_date or date.today(),
        status=payload.status,
    )
    return _to_out(receipt, order.po_number, order.vendor_id, vendor_name)
