"""Expense persistence via finance_transactions (debit, reference_type='expense')."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.finance_transaction import FinanceTransaction
from app.models.vendor import Vendor

EXPENSE_REFERENCE = "expense"
DEBIT = "debit"


class ExpenseRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(FinanceTransaction.organization_id, self.tenant_id)

    def _expense_filter(self):
        return and_(
            self._tenant_filter(),
            FinanceTransaction.transaction_type == DEBIT,
            FinanceTransaction.reference_type == EXPENSE_REFERENCE,
        )

    def _with_vendor_name(self):
        return (
            select(FinanceTransaction, Vendor.name)
            .outerjoin(
                Vendor,
                and_(
                    Vendor.id == FinanceTransaction.reference_id,
                    Vendor.organization_id == self.tenant_id,
                ),
            )
            .where(self._expense_filter())
        )

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[FinanceTransaction, str | None]], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(FinanceTransaction).where(self._expense_filter())
        ) or 0
        stmt = (
            self._with_vendor_name()
            .order_by(FinanceTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1]) for row in rows], int(total)

    async def get_with_vendor_name(
        self, expense_id: UUID
    ) -> tuple[FinanceTransaction, str | None] | None:
        stmt = self._with_vendor_name().where(FinanceTransaction.id == expense_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def create_debit(
        self,
        *,
        account_id: UUID,
        amount: Decimal,
        transaction_date: date,
        description: str | None,
        vendor_id: UUID | None,
    ) -> FinanceTransaction:
        row = FinanceTransaction(
            organization_id=self.tenant_id,
            account_id=account_id,
            transaction_type=DEBIT,
            amount=amount,
            reference_type=EXPENSE_REFERENCE,
            reference_id=vendor_id,
            description=description,
            transaction_date=transaction_date,
            reconciled=False,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row
