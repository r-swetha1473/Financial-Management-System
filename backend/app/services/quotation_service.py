"""Quotation application service. Tenant comes from the session only."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.repositories.quotations import QuotationRepository
from app.schemas.quotation import QuotationCreate, QuotationOut

_DRAFT = "draft"


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
        plan_duration=row.plan_duration,
        billing_cycle=row.billing_cycle,
        deposit_amount=row.deposit_amount,
        created_at=row.created_at,
    )


async def list_quotations(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    customer_id: UUID | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[QuotationOut], int]:
    rows, total = await QuotationRepository(session, tenant_id).list_page(
        page,
        page_size,
        customer_id=customer_id,
        status=status,
        search=search,
    )
    return [_to_out(quotation, customer_name) for quotation, customer_name in rows], total


async def get_quotation(session: AsyncSession, tenant_id: UUID, quotation_id: UUID) -> QuotationOut:
    named = await QuotationRepository(session, tenant_id).get_by_id(quotation_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscribed plan not found in this organization.",
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
        plan_duration=payload.plan_duration,
        billing_cycle=payload.billing_cycle,
        deposit_amount=payload.deposit_amount if payload.deposit_amount is not None else Decimal("0"),
    )
    return _to_out(row, customer.name)


async def decide_quotation(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    quotation_id: UUID,
    decision: Literal["accepted", "rejected"],
) -> QuotationOut:
    repo = QuotationRepository(session, tenant_id)
    quotation = await repo.get_for_update(quotation_id)
    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscribed plan not found in this organization.",
        )
    if quotation.status != _DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only a draft subscribed plan can be {decision} (current status is {quotation.status}).",
        )

    previous = quotation.status
    quotation.status = decision
    action = "accept" if decision == "accepted" else "reject"
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action=action,
        entity_name="quotation",
        entity_id=quotation.id,
        old_values={"status": previous},
        new_values={"status": decision, "quote_number": quotation.quote_number},
    )
    await session.commit()
    await session.refresh(quotation)

    named = await repo.get_by_id(quotation.id)
    if named is None:
        return _to_out(quotation, None)
    row, customer_name = named
    return _to_out(row, customer_name)
