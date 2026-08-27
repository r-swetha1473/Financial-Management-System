"""Customer application service. Tenant comes from CurrentUser only."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.customers import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerOut


def _to_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=str(customer.id),
        organization_id=str(customer.organization_id),
        name=customer.name,
        address=customer.address,
        gstin=customer.gst_number,
        state=customer.state,
        credit_limit=customer.credit_limit,
        created_at=customer.created_at,
    )


async def list_customers(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[CustomerOut], int]:
    rows, total = await CustomerRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(row) for row in rows], total


async def get_customer(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> CustomerOut:
    customer = await CustomerRepository(session, tenant_id).get_by_id(customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this organization.",
        )
    return _to_out(customer)


async def create_customer(session: AsyncSession, tenant_id: UUID, payload: CustomerCreate) -> CustomerOut:
    customer = await CustomerRepository(session, tenant_id).create(
        name=payload.name.strip(),
        address=payload.address,
        gst_number=payload.gstin,
        state=payload.state,
        credit_limit=payload.credit_limit,
    )
    return _to_out(customer)
