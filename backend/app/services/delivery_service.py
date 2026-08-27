"""Delivery application service. Tenant comes from the session only."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.delivery import Delivery
from app.repositories.deliveries import DeliveryRepository
from app.repositories.sales_orders import SalesOrderRepository
from app.schemas.delivery import DeliveryCreate, DeliveryOut

_DELIVERABLE = frozenset({"confirmed", "fulfilled"})


def _to_out(
    row: Delivery,
    order_number: str | None,
    customer_id: UUID | None,
    customer_name: str | None,
) -> DeliveryOut:
    return DeliveryOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        sales_order_id=str(row.sales_order_id),
        order_number=order_number or "",
        customer_id=str(customer_id) if customer_id else None,
        customer_name=customer_name or "",
        delivery_number=row.delivery_number,
        status=row.status,
        delivery_date=row.delivery_date,
        created_at=row.created_at,
    )


async def list_deliveries(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[DeliveryOut], int]:
    rows, total = await DeliveryRepository(session, tenant_id).list_page(page, page_size)
    return [
        _to_out(delivery, order_number, customer_id, customer_name)
        for delivery, order_number, customer_id, customer_name in rows
    ], total


async def get_delivery(session: AsyncSession, tenant_id: UUID, delivery_id: UUID) -> DeliveryOut:
    named = await DeliveryRepository(session, tenant_id).get_by_id(delivery_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found in this organization.",
        )
    delivery, order_number, customer_id, customer_name = named
    return _to_out(delivery, order_number, customer_id, customer_name)


async def create_delivery(
    session: AsyncSession,
    tenant_id: UUID,
    payload: DeliveryCreate,
) -> DeliveryOut:
    so_repo = SalesOrderRepository(session, tenant_id)
    order = await so_repo.get_for_update(payload.sales_order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales order not found in this organization.",
        )
    if order.status not in _DELIVERABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sales order must be confirmed or fulfilled before a delivery can be recorded.",
        )

    customer = await session.get(Customer, order.customer_id)
    customer_name = customer.name if customer and customer.organization_id == tenant_id else None

    delivery = await DeliveryRepository(session, tenant_id).create_against_sales_order(
        sales_order=order,
        delivery_date=payload.delivery_date or date.today(),
        status=payload.status,
    )
    return _to_out(delivery, order.order_number, order.customer_id, customer_name)
