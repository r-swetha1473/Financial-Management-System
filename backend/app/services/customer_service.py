"""Customer application service. Tenant comes from CurrentUser only."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.customers import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerOut, format_file_size


def _to_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=str(customer.id),
        organization_id=str(customer.organization_id),
        name=customer.name,
        address=customer.address,
        gstin=customer.gst_number,
        state=customer.state,
        credit_limit=customer.credit_limit,
        phone=customer.phone,
        drivers_license_number=customer.drivers_license_number,
        photo_file_name=customer.photo_file_name,
        photo_mime_type=customer.photo_mime_type,
        photo_document_id=str(customer.photo_document_id) if customer.photo_document_id else None,
        address_proof_name=customer.address_proof_file_name,
        address_proof_size=format_file_size(customer.address_proof_file_size),
        address_proof_type=customer.address_proof_mime_type,
        address_proof_document_id=(
            str(customer.address_proof_document_id) if customer.address_proof_document_id else None
        ),
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
        phone=payload.phone,
        drivers_license_number=payload.drivers_license_number,
    )
    return _to_out(customer)
