"""Supplier-payment application service. Does not post to finance_transactions."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.payment import Payment
from app.models.vendor import Vendor
from app.repositories.payables import PayableRepository
from app.repositories.payments import PaymentRepository
from app.repositories.supplier_invoices import SupplierInvoiceRepository
from app.schemas.payment import PaymentCreate, PaymentOut

_APPROVED = "approved"
_CANCELLED = "cancelled"


def _to_out(
    row: Payment,
    invoice_number: str | None,
    vendor_id: UUID | None,
    vendor_name: str | None,
) -> PaymentOut:
    return PaymentOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        supplier_invoice_id=str(row.supplier_invoice_id),
        invoice_number=invoice_number or "",
        vendor_id=str(vendor_id) if vendor_id else "",
        vendor_name=vendor_name or "",
        payment_date=row.payment_date,
        amount=row.amount,
        payment_mode=row.payment_mode,
        status=row.status,
        created_at=row.created_at,
    )


def _payable_status(amount: Decimal, outstanding: Decimal) -> str:
    if outstanding <= 0:
        return "closed"
    if outstanding < amount:
        return "partial"
    return "open"


def _invoice_payment_status(amount: Decimal, outstanding: Decimal) -> str:
    if outstanding <= 0:
        return "paid"
    if outstanding < amount:
        return "partially_paid"
    return "pending"


async def list_payments(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[PaymentOut], int]:
    rows, total = await PaymentRepository(session, tenant_id).list_page(page, page_size, search=search)
    return [
        _to_out(payment, invoice_number, vendor_id, vendor_name)
        for payment, invoice_number, vendor_id, vendor_name in rows
    ], total


async def get_payment(session: AsyncSession, tenant_id: UUID, payment_id: UUID) -> PaymentOut:
    named = await PaymentRepository(session, tenant_id).get_with_names(payment_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found in this organization.",
        )
    payment, invoice_number, vendor_id, vendor_name = named
    return _to_out(payment, invoice_number, vendor_id, vendor_name)


async def create_payment(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    payload: PaymentCreate,
) -> PaymentOut:
    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero.",
        )

    invoice_repo = SupplierInvoiceRepository(session, tenant_id)
    invoice = await invoice_repo.get_for_update(payload.supplier_invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier invoice not found in this organization.",
        )
    if invoice.status == _CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record a payment against a cancelled supplier invoice.",
        )
    if invoice.approval_status != _APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Payment can only be recorded against an approved supplier invoice "
                f"(current approval_status is {invoice.approval_status})."
            ),
        )

    payable = await PayableRepository(session, tenant_id).lock_or_create_for_invoice(invoice)
    payment_repo = PaymentRepository(session, tenant_id)
    paid = await payment_repo.completed_sum_for_invoice(invoice.id)
    live_outstanding = payable.amount - paid
    if payload.amount > live_outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment cannot exceed the outstanding invoice amount.",
        )

    payment = await payment_repo.create_completed(
        supplier_invoice_id=invoice.id,
        payment_date=payload.payment_date or date.today(),
        amount=payload.amount,
        payment_mode=payload.payment_mode,
    )
    new_outstanding = live_outstanding - payload.amount
    payable.outstanding = new_outstanding
    payable.status = _payable_status(payable.amount, new_outstanding)
    invoice.status = _invoice_payment_status(invoice.amount, new_outstanding)

    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action="create",
        entity_name="p2p_payment",
        entity_id=payment.id,
        old_values=None,
        new_values={
            "supplier_invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount": str(payload.amount),
            "outstanding": str(new_outstanding),
        },
    )
    await session.commit()
    await session.refresh(payment)

    vendor = await session.get(Vendor, invoice.vendor_id)
    return _to_out(
        payment,
        invoice.invoice_number,
        invoice.vendor_id,
        vendor.name if vendor else None,
    )
