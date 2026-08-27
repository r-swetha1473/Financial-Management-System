"""Quotation application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.quotation import Quotation
from app.repositories.quotations import QuotationRepository
from app.schemas.quotation import QuotationCreate, QuotationOut


def _to_out(row: Quotation, customer_name: str | None) -> QuotationOut:
    return QuotationOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        customer_id=str(row.customer_id),
        customer_name=customer_name or "",
        quote_number=row.quote_number,
        status=row.status,
        quote_date=row.quote_date,
        valid_until=row.valid_until,
        total_amount=row.total_amount,
        created_at=row.created_at,
    )


async def list_quotations(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[QuotationOut], int]:
    rows, total = await QuotationRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(quotation, customer_name) for quotation, customer_name in rows], total


async def get_quotation(session: AsyncSession, tenant_id: UUID, quotation_id: UUID) -> QuotationOut:
    named = await QuotationRepository(session, tenant_id).get_by_id(quotation_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found in this organization.",
        )
    quotation, customer_name = named
    return _to_out(quotation, customer_name)


async def create_quotation(
    session: AsyncSession,
    tenant_id: UUID,
    payload: QuotationCreate,
) -> QuotationOut:
    customer = await session.get(Customer, payload.customer_id)
    if customer is None or customer.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this organization.",
        )

    row = await QuotationRepository(session, tenant_id).create(
        customer_id=customer.id,
        quote_date=payload.quote_date or date.today(),
        valid_until=payload.valid_until,
        total_amount=payload.total_amount if payload.total_amount is not None else Decimal("0"),
        status=payload.status,
    )
    return _to_out(row, customer.name)
