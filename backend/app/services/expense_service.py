"""Expense application service. Posts debit rows to finance_transactions; not a P2P document."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.finance_transaction import FinanceTransaction
from app.repositories.expenses import ExpenseRepository
from app.repositories.finance_accounts import FinanceAccountRepository
from app.schemas.expense import ExpenseCreate, ExpenseOut


def _to_out(row: FinanceTransaction, vendor_name: str | None) -> ExpenseOut:
    return ExpenseOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        vendor_id=str(row.reference_id) if row.reference_id else None,
        vendor_name=vendor_name or "",
        product_service_name=row.description or "",
        cost=row.amount,
        expense_date=row.transaction_date,
        status="approved",
        created_at=row.created_at,
    )


async def list_expenses(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[ExpenseOut], int]:
    rows, total = await ExpenseRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(row, vendor_name) for row, vendor_name in rows], total


async def get_expense(session: AsyncSession, tenant_id: UUID, expense_id: UUID) -> ExpenseOut:
    named = await ExpenseRepository(session, tenant_id).get_with_vendor_name(expense_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found in this organization.",
        )
    row, vendor_name = named
    return _to_out(row, vendor_name)


async def create_expense(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    payload: ExpenseCreate,
) -> ExpenseOut:
    if payload.cost <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense cost must be greater than zero.",
        )

    description = (payload.product_service_name or "").strip() or None
    account = await FinanceAccountRepository(session, tenant_id).get_or_create_operating_cash()
    row = await ExpenseRepository(session, tenant_id).create_debit(
        account_id=account.id,
        amount=payload.cost,
        transaction_date=payload.expense_date,
        description=description,
        vendor_id=payload.vendor_id,
    )
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action="create",
        entity_name="finance_expense",
        entity_id=row.id,
        old_values=None,
        new_values={
            "amount": str(payload.cost),
            "transaction_type": "debit",
            "expense_date": payload.expense_date.isoformat(),
        },
    )
    await session.commit()
    await session.refresh(row)

    named = await ExpenseRepository(session, tenant_id).get_with_vendor_name(row.id)
    vendor_name = named[1] if named else None
    return _to_out(row, vendor_name)
