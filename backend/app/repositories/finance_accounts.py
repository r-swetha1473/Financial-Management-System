"""Finance-account persistence. Tenant is injected at construction."""

from decimal import Decimal

from sqlalchemy import select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.finance_account import FinanceAccount

OPERATING_CASH_NAME = "Operating cash"


class FinanceAccountRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(FinanceAccount.organization_id, self.tenant_id)

    async def get_or_create_operating_cash(self) -> FinanceAccount:
        """Internal cash account so expenses can satisfy finance_transactions.account_id.

        Not an Accounts module — one row per tenant, created on first expense.
        """
        stmt = (
            select(FinanceAccount)
            .where(self._tenant_filter(), FinanceAccount.name == OPERATING_CASH_NAME)
            .with_for_update()
        )
        account = await self.session.scalar(stmt)
        if account is not None:
            return account
        account = FinanceAccount(
            organization_id=self.tenant_id,
            name=OPERATING_CASH_NAME,
            account_type="cash",
            account_number=None,
            balance=Decimal("0"),
            is_active=True,
        )
        self.session.add(account)
        await self.session.flush()
        await self.session.refresh(account)
        return account
