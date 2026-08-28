"""Supplier-invoice application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.purchase_order import PurchaseOrder
from app.models.supplier_invoice import SupplierInvoice
from app.models.vendor import Vendor
from app.repositories.goods_receipts import GoodsReceiptRepository
from app.repositories.supplier_invoices import SupplierInvoiceRepository
from app.schemas.supplier_invoice import SupplierInvoiceCreate, SupplierInvoiceOut

_RECEIVED = "received"


def _to_out(
    row: SupplierInvoice,
    vendor_name: str | None,
    po_number: str | None,
    grn_number: str | None,
) -> SupplierInvoiceOut:
    return SupplierInvoiceOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        vendor_id=str(row.vendor_id),
        vendor_name=vendor_name or "",
        purchase_order_id=str(row.purchase_order_id) if row.purchase_order_id else None,
        po_number=po_number or "",
        goods_receipt_id=str(row.goods_receipt_id) if row.goods_receipt_id else None,
        grn_number=grn_number or "",
        invoice_number=row.invoice_number,
        status=row.status,
        approval_status=row.approval_status,
        invoice_date=row.invoice_date,
        amount=row.amount,
        gst_amount=row.gst_amount,
        created_at=row.created_at,
    )


async def list_supplier_invoices(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    vendor_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[SupplierInvoiceOut], int]:
    rows, total = await SupplierInvoiceRepository(session, tenant_id).list_page(
        page, page_size, vendor_id=vendor_id, status=status, search=search
    )
    return [
        _to_out(invoice, vendor_name, po_number, grn_number)
        for invoice, vendor_name, po_number, grn_number in rows
    ], total


async def get_supplier_invoice(session: AsyncSession, tenant_id: UUID, invoice_id: UUID) -> SupplierInvoiceOut:
    named = await SupplierInvoiceRepository(session, tenant_id).get_with_names(invoice_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier invoice not found in this organization.",
        )
    invoice, vendor_name, po_number, grn_number = named
    return _to_out(invoice, vendor_name, po_number, grn_number)


async def create_supplier_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: SupplierInvoiceCreate,
) -> SupplierInvoiceOut:
    grn_repo = GoodsReceiptRepository(session, tenant_id)
    invoice_repo = SupplierInvoiceRepository(session, tenant_id)
    receipt = await grn_repo.get_for_update(payload.goods_receipt_id)
    if receipt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goods receipt not found in this organization.",
        )
    if receipt.status != _RECEIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Goods receipt must be received before a supplier invoice can be recorded.",
        )

    existing = await invoice_repo.active_for_receipt(receipt.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This goods receipt already has a supplier invoice.",
        )

    order = await session.get(PurchaseOrder, receipt.purchase_order_id)
    if order is None or order.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase order not found in this organization.",
        )

    vendor_id = payload.vendor_id or order.vendor_id
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None or vendor.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found in this organization.",
        )
    if vendor_id != order.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor does not match the purchase order.",
        )

    invoice = await invoice_repo.create_from_receipt(
        goods_receipt=receipt,
        vendor_id=vendor_id,
        purchase_order_id=order.id,
        invoice_date=payload.invoice_date or date.today(),
        amount=payload.amount if payload.amount is not None else Decimal("0"),
        gst_amount=payload.gst_amount if payload.gst_amount is not None else Decimal("0"),
    )
    return _to_out(invoice, vendor.name, order.po_number, receipt.grn_number)


async def decide_supplier_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    invoice_id: UUID,
    decision: Literal["approved", "rejected"],
) -> SupplierInvoiceOut:
    """Set approval_status only. Does not touch payables, GRN, or PO."""
    repo = SupplierInvoiceRepository(session, tenant_id)
    invoice = await repo.get_for_update(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier invoice not found in this organization.",
        )
    if invoice.approval_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier invoice has already been {invoice.approval_status}.",
        )

    previous = invoice.approval_status
    invoice.approval_status = decision
    action = "approve" if decision == "approved" else "reject"
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action=action,
        entity_name="supplier_invoice",
        entity_id=invoice.id,
        old_values={"approval_status": previous},
        new_values={"approval_status": decision, "invoice_number": invoice.invoice_number},
    )
    await session.commit()
    await session.refresh(invoice)

    named = await repo.get_with_names(invoice.id)
    if named is None:
        return _to_out(invoice, None, None, None)
    row, vendor_name, po_number, grn_number = named
    return _to_out(row, vendor_name, po_number, grn_number)
