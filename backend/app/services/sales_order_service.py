"""Sales-order application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.quotation import Quotation
from app.models.sales_order import SalesOrder
from app.repositories.quotations import QuotationRepository
from app.repositories.sales_orders import SalesOrderRepository
from app.schemas.sales_order import SalesOrderCreate, SalesOrderOut

_ACCEPTED = "accepted"


def _to_out(row: SalesOrder, customer_name: str | None, quote_number: str | None) -> SalesOrderOut:
    return SalesOrderOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        customer_id=str(row.customer_id),
        customer_name=customer_name or "",
        quotation_id=str(row.quotation_id) if row.quotation_id else None,
        quote_number=quote_number or "",
        order_number=row.order_number,
        status=row.status,
        order_date=row.order_date,
        total_amount=row.total_amount,
        created_at=row.created_at,
    )


async def list_sales_orders(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[SalesOrderOut], int]:
    rows, total = await SalesOrderRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(order, customer_name, quote_number) for order, customer_name, quote_number in rows], total


async def get_sales_order(session: AsyncSession, tenant_id: UUID, order_id: UUID) -> SalesOrderOut:
    named = await SalesOrderRepository(session, tenant_id).get_by_id(order_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found in this organization.",
        )
    order, customer_name, quote_number = named
    return _to_out(order, customer_name, quote_number)


async def _customer_in_tenant(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is None or customer.organization_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this organization.",
        )
    return customer


async def create_sales_order(
    session: AsyncSession,
    tenant_id: UUID,
    payload: SalesOrderCreate,
) -> SalesOrderOut:
    quotation: Quotation | None = None
    if payload.quotation_id is not None:
        quotation = await QuotationRepository(session, tenant_id).get_for_update(payload.quotation_id)
        if quotation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation not found in this organization.",
            )
        if quotation.status != _ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation must be accepted before converting to a sales order.",
            )
        if payload.customer_id is not None and payload.customer_id != quotation.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer does not match the quotation.",
            )
        customer = await _customer_in_tenant(session, tenant_id, quotation.customer_id)
    else:
        if payload.customer_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A customer is required to create a sales order.",
            )
        customer = await _customer_in_tenant(session, tenant_id, payload.customer_id)

    order = await SalesOrderRepository(session, tenant_id).create(
        customer_id=customer.id,
        quotation=quotation,
        order_date=payload.order_date or date.today(),
        total_amount=payload.total_amount if payload.total_amount is not None else Decimal("0"),
        status=payload.status,
    )
    return _to_out(order, customer.name, quotation.quote_number if quotation is not None else None)
