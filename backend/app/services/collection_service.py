"""Customer-collection application service. Does not post to finance_transactions."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.collection import Collection
from app.models.customer import Customer
from app.repositories.collections import CollectionRepository
from app.repositories.receivables import ReceivableRepository
from app.repositories.sales_invoices import SalesInvoiceRepository
from app.schemas.collection import CollectionCreate, CollectionOut

_APPROVED = "approved"
_CANCELLED = "cancelled"


def _to_out(
    row: Collection,
    invoice_number: str | None,
    customer_id: UUID | None,
    customer_name: str | None,
) -> CollectionOut:
    return CollectionOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        sales_invoice_id=str(row.sales_invoice_id),
        invoice_number=invoice_number or "",
        customer_id=str(customer_id) if customer_id else "",
        customer_name=customer_name or "",
        collection_date=row.collection_date,
        amount=row.amount,
        payment_mode=row.payment_mode,
        status=row.status,
        created_at=row.created_at,
    )


def _receivable_status(amount: Decimal, outstanding: Decimal) -> str:
    if outstanding <= 0:
        return "closed"
    if outstanding < amount:
        return "partial"
    return "open"


def _invoice_collection_status(amount: Decimal, outstanding: Decimal) -> str:
    if outstanding <= 0:
        return "paid"
    if outstanding < amount:
        return "partially_paid"
    return "pending"


async def list_collections(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[CollectionOut], int]:
    rows, total = await CollectionRepository(session, tenant_id).list_page(page, page_size)
    return [
        _to_out(collection, invoice_number, customer_id, customer_name)
        for collection, invoice_number, customer_id, customer_name in rows
    ], total


async def get_collection(
    session: AsyncSession,
    tenant_id: UUID,
    collection_id: UUID,
) -> CollectionOut:
    named = await CollectionRepository(session, tenant_id).get_with_names(collection_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found in this organization.",
        )
    collection, invoice_number, customer_id, customer_name = named
    return _to_out(collection, invoice_number, customer_id, customer_name)


async def create_collection(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    payload: CollectionCreate,
) -> CollectionOut:
    if payload.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection amount must be greater than zero.",
        )

    invoice_repo = SalesInvoiceRepository(session, tenant_id)
    invoice = await invoice_repo.get_for_update(payload.sales_invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales invoice not found in this organization.",
        )
    if invoice.status == _CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record a collection against a cancelled sales invoice.",
        )
    if invoice.approval_status != _APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Collection can only be recorded against an approved sales invoice "
                f"(current approval_status is {invoice.approval_status})."
            ),
        )

    receivable = await ReceivableRepository(session, tenant_id).lock_or_create_for_invoice(invoice)
    collection_repo = CollectionRepository(session, tenant_id)
    collected = await collection_repo.completed_sum_for_invoice(invoice.id)
    live_outstanding = receivable.amount - collected
    if payload.amount > live_outstanding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection cannot exceed the outstanding invoice amount.",
        )

    collection = await collection_repo.create_completed(
        sales_invoice_id=invoice.id,
        collection_date=payload.collection_date or date.today(),
        amount=payload.amount,
        payment_mode=payload.payment_mode,
    )
    new_outstanding = live_outstanding - payload.amount
    receivable.outstanding = new_outstanding
    receivable.status = _receivable_status(receivable.amount, new_outstanding)
    invoice.status = _invoice_collection_status(invoice.amount, new_outstanding)

    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action="create",
        entity_name="o2c_collection",
        entity_id=collection.id,
        old_values=None,
        new_values={
            "sales_invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount": str(payload.amount),
            "outstanding": str(new_outstanding),
        },
    )
    await session.commit()
    await session.refresh(collection)

    customer = await session.get(Customer, invoice.customer_id)
    return _to_out(
        collection,
        invoice.invoice_number,
        invoice.customer_id,
        customer.name if customer else None,
    )
