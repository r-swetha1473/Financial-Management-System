"""Legacy bookings, booking invoices, and receipts. Tables already existed; this is the first API."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.catalog import CatalogRepository
from app.repositories.customers import CustomerRepository
from app.repositories.legacy_bookings import LegacyBookingRepository
from app.schemas.legacy_booking import (
    BookingCreate,
    BookingOut,
    LegacyInvoiceCreate,
    LegacyInvoiceOut,
    ReceiptCreate,
    ReceiptOut,
)


def _invoice_status(amount: Decimal, paid: Decimal) -> str:
    outstanding = amount - paid
    if outstanding <= 0:
        return "paid"
    if paid > 0:
        return "partially_paid"
    return "pending"


def _booking_out(row, customer_name: str, offering_name: str) -> BookingOut:
    return BookingOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        offering_id=str(row.offering_id) if row.offering_id else None,
        offering_name=offering_name or "",
        customer_id=str(row.customer_id) if row.customer_id else None,
        customer_name=customer_name or "",
        booking_start_date=row.booking_start_date,
        booking_end_date=row.booking_end_date,
        security_paid=row.security_paid,
        created_at=row.created_at,
    )


def _invoice_out(row, customer_name: str, booking_label: str, paid: Decimal) -> LegacyInvoiceOut:
    paid_amt = Decimal(str(paid or 0))
    outstanding = row.invoice_amount - paid_amt
    if outstanding < 0:
        outstanding = Decimal("0")
    return LegacyInvoiceOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        invoice_number=row.invoice_number,
        customer_id=str(row.customer_id) if row.customer_id else None,
        customer_name=customer_name or "",
        booking_id=str(row.booking_id) if row.booking_id else None,
        booking_label=booking_label or "",
        plan_id=str(row.plan_id) if row.plan_id else None,
        plan_name="",
        invoice_raised_date=row.invoice_raised_date,
        security_amount_deposited=row.security_amount_deposited,
        invoice_amount=row.invoice_amount,
        is_gst_invoice=row.is_gst_invoice,
        gst_amount=row.gst_amount,
        paid=paid_amt,
        outstanding=outstanding,
        status=_invoice_status(row.invoice_amount, paid_amt),
        created_at=row.created_at,
    )


async def list_bookings(session, tenant_id, page, page_size, customer_id: UUID | None):
    rows, total = await LegacyBookingRepository(session, tenant_id).list_bookings(page, page_size, customer_id)
    return [_booking_out(row, cust or "", off or "") for row, cust, off in rows], total


async def get_booking(session, tenant_id, booking_id: UUID) -> BookingOut:
    named = await LegacyBookingRepository(session, tenant_id).get_booking_named(booking_id)
    if named is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found in this organization.")
    row, cust, off = named
    return _booking_out(row, cust or "", off or "")


async def create_booking(session: AsyncSession, tenant_id, payload: BookingCreate) -> BookingOut:
    customer = await CustomerRepository(session, tenant_id).get_by_id(payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found in this organization.")
    if payload.offering_id is not None:
        offering = await CatalogRepository(session, tenant_id).get_offering(payload.offering_id)
        if offering is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offering not found in this organization.")
    repo = LegacyBookingRepository(session, tenant_id)
    row = await repo.create_booking(
        offering_id=payload.offering_id,
        customer_id=payload.customer_id,
        booking_start_date=payload.booking_start_date,
        booking_end_date=payload.booking_end_date,
        security_paid=payload.security_paid,
    )
    return await get_booking(session, tenant_id, row.id)


async def list_invoices(session, tenant_id, page, page_size, customer_id: UUID | None):
    rows, total = await LegacyBookingRepository(session, tenant_id).list_invoices(page, page_size, customer_id)
    items = []
    for row, cust, _booking_id, offering_name, paid in rows:
        items.append(_invoice_out(row, cust or "", offering_name or "", Decimal(str(paid or 0))))
    return items, total


async def get_invoice(session, tenant_id, invoice_id: UUID) -> LegacyInvoiceOut:
    repo = LegacyBookingRepository(session, tenant_id)
    named = await repo.get_invoice_named(invoice_id)
    if named is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found in this organization.")
    row, cust, offering_name = named
    paid = await repo.paid_on_invoice(row.id)
    return _invoice_out(row, cust or "", offering_name or "", paid)


async def create_invoice(session, tenant_id, payload: LegacyInvoiceCreate) -> LegacyInvoiceOut:
    repo = LegacyBookingRepository(session, tenant_id)
    if payload.customer_id is not None:
        customer = await CustomerRepository(session, tenant_id).get_by_id(payload.customer_id)
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found in this organization.")
    if payload.booking_id is not None:
        booking = await repo.get_booking_named(payload.booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found in this organization.")
    number = (payload.invoice_number or "").strip() or await repo.next_invoice_number()
    gst = payload.gst_amount if payload.is_gst_invoice else Decimal("0")
    try:
        row = await repo.create_invoice(
            invoice_number=number,
            customer_id=payload.customer_id,
            booking_id=payload.booking_id,
            plan_id=payload.plan_id,
            invoice_raised_date=payload.invoice_raised_date,
            security_amount_deposited=payload.security_amount_deposited,
            invoice_amount=payload.invoice_amount,
            is_gst_invoice=payload.is_gst_invoice,
            gst_amount=gst,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invoice with this number already exists in this organization.",
        ) from exc
    return await get_invoice(session, tenant_id, row.id)


async def list_receipts(session, tenant_id, page, page_size):
    rows, total = await LegacyBookingRepository(session, tenant_id).list_receipts(page, page_size)
    items = [
        ReceiptOut(
            id=str(row.id),
            organization_id=str(row.organization_id),
            invoice_id=str(row.invoice_id),
            invoice_number=number or "",
            receipt_date=row.receipt_date,
            receipt_amount=row.receipt_amount,
            pending_amount=row.pending_amount,
            payment_mode=row.payment_mode,
            transaction_last4=row.transaction_last4,
            entered_by=entered or "",
            created_at=row.created_at,
        )
        for row, number, entered in rows
    ]
    return items, total


async def get_receipt(session, tenant_id, receipt_id: UUID) -> ReceiptOut:
    named = await LegacyBookingRepository(session, tenant_id).get_receipt_named(receipt_id)
    if named is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found in this organization.")
    row, number, entered = named
    return ReceiptOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        invoice_id=str(row.invoice_id),
        invoice_number=number or "",
        receipt_date=row.receipt_date,
        receipt_amount=row.receipt_amount,
        pending_amount=row.pending_amount,
        payment_mode=row.payment_mode,
        transaction_last4=row.transaction_last4,
        entered_by=entered or "",
        created_at=row.created_at,
    )


async def create_receipt(session, tenant_id, actor_id: UUID | None, payload: ReceiptCreate) -> ReceiptOut:
    if payload.payment_mode == "UPI" and not (payload.transaction_last4 and payload.transaction_last4.isdigit() and len(payload.transaction_last4) == 4):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UPI receipts require exactly 4 digits.")
    if payload.receipt_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero.")
    repo = LegacyBookingRepository(session, tenant_id)
    invoice = await repo.get_invoice(payload.invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found in this organization.")
    paid = await repo.paid_on_invoice(invoice.id)
    outstanding = invoice.invoice_amount - paid
    if payload.receipt_amount > outstanding:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receipt exceeds invoice outstanding.")
    pending = outstanding - payload.receipt_amount
    row = await repo.create_receipt(
        invoice_id=invoice.id,
        receipt_date=payload.receipt_date,
        receipt_amount=payload.receipt_amount,
        pending_amount=pending,
        payment_mode=payload.payment_mode,
        transaction_last4=payload.transaction_last4,
        entered_by=actor_id,
    )
    return await get_receipt(session, tenant_id, row.id)
