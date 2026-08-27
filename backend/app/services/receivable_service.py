"""Receivable read service. Live outstanding is source of truth; stored column is a cache."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receivable import Receivable
from app.repositories.collections import CollectionRepository
from app.repositories.receivables import SOURCE_SALES_INVOICE, ReceivableRepository
from app.schemas.receivable import ReceivableOut


def _to_out(
    row: Receivable,
    invoice_number: str | None,
    customer_name: str | None,
    outstanding: Decimal,
) -> ReceivableOut:
    return ReceivableOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        source_type=row.source_type,
        source_id=str(row.source_id),
        invoice_number=invoice_number or "",
        customer_id=str(row.customer_id) if row.customer_id else "",
        customer_name=customer_name or "",
        amount=row.amount,
        outstanding=outstanding,
        due_date=row.due_date,
        status=_status(row.amount, outstanding),
        created_at=row.created_at,
    )


def _status(amount: Decimal, outstanding: Decimal) -> str:
    if outstanding <= 0:
        return "closed"
    if outstanding < amount:
        return "partial"
    return "open"


async def list_receivables(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[ReceivableOut], int]:
    rows, total = await ReceivableRepository(session, tenant_id).list_page(page, page_size)
    collection_repo = CollectionRepository(session, tenant_id)
    invoice_ids = [row.source_id for row, *_ in rows if row.source_type == SOURCE_SALES_INVOICE]
    collected = await collection_repo.completed_sums_for_invoices(invoice_ids)
    items = []
    for receivable, invoice_number, customer_name in rows:
        paid = collected.get(receivable.source_id, Decimal("0"))
        outstanding = receivable.amount - paid
        items.append(_to_out(receivable, invoice_number, customer_name, outstanding))
    return items, total


async def get_receivable(
    session: AsyncSession,
    tenant_id: UUID,
    receivable_id: UUID,
) -> ReceivableOut:
    named = await ReceivableRepository(session, tenant_id).get_with_names(receivable_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receivable not found in this organization.",
        )
    receivable, invoice_number, customer_name = named
    paid = Decimal("0")
    if receivable.source_type == SOURCE_SALES_INVOICE:
        paid = await CollectionRepository(session, tenant_id).completed_sum_for_invoice(receivable.source_id)
    outstanding = receivable.amount - paid
    return _to_out(receivable, invoice_number, customer_name, outstanding)
