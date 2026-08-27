"""Sales-invoice application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.customer import Customer
from app.models.sales_invoice import SalesInvoice
from app.models.sales_order import SalesOrder
from app.repositories.collections import CollectionRepository
from app.repositories.deliveries import DeliveryRepository
from app.repositories.sales_invoices import SalesInvoiceRepository
from app.schemas.sales_invoice import SalesInvoiceCreate, SalesInvoiceOut

_DELIVERED = "delivered"


def _to_out(
    row: SalesInvoice,
    customer_name: str | None,
    order_number: str | None,
    delivery_number: str | None,
    outstanding: Decimal,
) -> SalesInvoiceOut:
    return SalesInvoiceOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        customer_id=str(row.customer_id),
        customer_name=customer_name or "",
        sales_order_id=str(row.sales_order_id) if row.sales_order_id else None,
        order_number=order_number or "",
        delivery_id=str(row.delivery_id) if row.delivery_id else None,
        delivery_number=delivery_number or "",
        invoice_number=row.invoice_number,
        status=row.status,
        approval_status=row.approval_status,
        invoice_date=row.invoice_date,
        amount=row.amount,
        gst_amount=row.gst_amount,
        outstanding=outstanding,
        created_at=row.created_at,
    )


async def _outstanding_map(session: AsyncSession, tenant_id: UUID, invoice_ids: list[UUID]) -> dict[UUID, Decimal]:
    return await CollectionRepository(session, tenant_id).completed_sums_for_invoices(invoice_ids)


def _live_outstanding(amount: Decimal, collected: Decimal) -> Decimal:
    return amount - collected


async def list_sales_invoices(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[SalesInvoiceOut], int]:
    rows, total = await SalesInvoiceRepository(session, tenant_id).list_page(page, page_size)
    collected = await _outstanding_map(session, tenant_id, [invoice.id for invoice, *_ in rows])
    return [
        _to_out(
            invoice,
            customer_name,
            order_number,
            delivery_number,
            _live_outstanding(invoice.amount, collected.get(invoice.id, Decimal("0"))),
        )
        for invoice, customer_name, order_number, delivery_number in rows
    ], total


async def get_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    invoice_id: UUID,
) -> SalesInvoiceOut:
    named = await SalesInvoiceRepository(session, tenant_id).get_with_names(invoice_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice not found in this organization.",
        )
    invoice, customer_name, order_number, delivery_number = named
    collected = await CollectionRepository(session, tenant_id).completed_sum_for_invoice(invoice.id)
    return _to_out(
        invoice,
        customer_name,
        order_number,
        delivery_number,
        _live_outstanding(invoice.amount, collected),
    )


async def create_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    payload: SalesInvoiceCreate,
) -> SalesInvoiceOut:
    delivery_repo = DeliveryRepository(session, tenant_id)
    invoice_repo = SalesInvoiceRepository(session, tenant_id)
    delivery = await delivery_repo.get_for_update(payload.delivery_id)
    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found in this organization.",
        )
    if delivery.status != _DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery must be delivered before a sales invoice can be recorded.",
        )

    existing = await invoice_repo.active_for_delivery(delivery.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This delivery already has a sales invoice.",
        )

    order = await session.get(SalesOrder, delivery.sales_order_id)
    if order is None or order.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found in this organization.",
        )

    if payload.sales_order_id is not None and payload.sales_order_id != order.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sales order does not match the delivery.",
        )
    if payload.customer_id is not None and payload.customer_id != order.customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer does not match the sales order.",
        )

    customer = await session.get(Customer, order.customer_id)
    if customer is None or customer.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this organization.",
        )

    invoice = await invoice_repo.create_from_delivery(
        delivery=delivery,
        customer_id=order.customer_id,
        sales_order_id=order.id,
        invoice_date=payload.invoice_date or date.today(),
        amount=payload.amount if payload.amount is not None else Decimal("0"),
        gst_amount=payload.gst_amount if payload.gst_amount is not None else Decimal("0"),
    )
    return _to_out(invoice, customer.name, order.order_number, delivery.delivery_number, invoice.amount)


async def decide_sales_invoice(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    invoice_id: UUID,
    decision: Literal["approved", "rejected"],
) -> SalesInvoiceOut:
    """Set approval_status only. Does not touch receivables, delivery, or SO."""
    repo = SalesInvoiceRepository(session, tenant_id)
    invoice = await repo.get_for_update(invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice not found in this organization.",
        )
    if invoice.approval_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sales invoice has already been {invoice.approval_status}.",
        )

    previous = invoice.approval_status
    invoice.approval_status = decision
    action = "approve" if decision == "approved" else "reject"
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action=action,
        entity_name="sales_invoice",
        entity_id=invoice.id,
        old_values={"approval_status": previous},
        new_values={"approval_status": decision, "invoice_number": invoice.invoice_number},
    )
    await session.commit()
    await session.refresh(invoice)

    named = await repo.get_with_names(invoice.id)
    collected = await CollectionRepository(session, tenant_id).completed_sum_for_invoice(invoice.id)
    outstanding = _live_outstanding(invoice.amount, collected)
    if named is None:
        return _to_out(invoice, None, None, None, outstanding)
    row, customer_name, order_number, delivery_number = named
    return _to_out(row, customer_name, order_number, delivery_number, outstanding)
