"""Finance open-pass persistence: transactions list, income union, GST sums, notes."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, text

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.finance_account import FinanceAccount
from app.models.finance_transaction import FinanceTransaction
from app.models.reconciliation_note import ReconciliationNote
from app.models.reference_data import ReferenceData
from app.models.document import Document


class FinanceOpenRepository(TenantScopedRepository):
    async def list_transactions(
        self, page: int, page_size: int, account_id: UUID | None, search: str
    ) -> tuple[list[tuple], int]:
        tenant = for_tenant(FinanceTransaction.organization_id, self.tenant_id)
        filters = [tenant]
        if account_id:
            filters.append(FinanceTransaction.account_id == account_id)
        if search.strip():
            filters.append(FinanceTransaction.description.ilike(f"%{search.strip()}%"))
        total = await self.session.scalar(select(func.count()).select_from(FinanceTransaction).where(*filters)) or 0
        stmt = (
            select(FinanceTransaction, FinanceAccount.name)
            .join(FinanceAccount, FinanceAccount.id == FinanceTransaction.account_id)
            .where(*filters)
            .order_by(FinanceTransaction.transaction_date.desc(), FinanceTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).all()), int(total)

    async def get_or_create_note(self) -> ReconciliationNote:
        row = await self.session.get(ReconciliationNote, self.tenant_id)
        if row is None:
            row = ReconciliationNote(organization_id=self.tenant_id, note="")
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def save_note(self, note: str) -> ReconciliationNote:
        row = await self.session.get(ReconciliationNote, self.tenant_id)
        if row is None:
            row = ReconciliationNote(organization_id=self.tenant_id, note=note)
            self.session.add(row)
        else:
            row.note = note
        await self.session.commit()
        await self.session.refresh(row)
        return row


class ReferenceDataRepository(TenantScopedRepository):
    def _tenant(self):
        return for_tenant(ReferenceData.organization_id, self.tenant_id)

    async def list_page(self, page: int, page_size: int, search: str) -> tuple[list[ReferenceData], int]:
        tenant = self._tenant()
        filters = [tenant]
        if search.strip():
            like = f"%{search.strip()}%"
            filters.append(
                ReferenceData.data_type.ilike(like) | ReferenceData.code.ilike(like) | ReferenceData.label.ilike(like)
            )
        total = await self.session.scalar(select(func.count()).select_from(ReferenceData).where(*filters)) or 0
        stmt = (
            select(ReferenceData)
            .where(*filters)
            .order_by(ReferenceData.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(stmt)).all()), int(total)

    async def create(self, **kwargs) -> ReferenceData:
        row = ReferenceData(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row


class DocumentListRepository(TenantScopedRepository):
    async def list_page(self, page: int, page_size: int, search: str) -> tuple[list[Document], int]:
        tenant = for_tenant(Document.organization_id, self.tenant_id)
        filters = [tenant]
        if search.strip():
            like = f"%{search.strip()}%"
            filters.append(Document.file_name.ilike(like) | Document.entity_name.ilike(like))
        total = await self.session.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
        stmt = (
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(stmt)).all()), int(total)
