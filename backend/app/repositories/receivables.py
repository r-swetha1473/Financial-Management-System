"""Receivable persistence. Lock the row for money mutations; outstanding is a cache."""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.customer import Customer
from app.models.receivable import Receivable
from app.models.sales_invoice import SalesInvoice

SOURCE_SALES_INVOICE = "sales_invoice"


class ReceivableRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Receivable.organization_id, self.tenant_id)

    async def lock_or_create_for_invoice(self, invoice: SalesInvoice) -> Receivable:
        stmt = (
            pg_insert(Receivable)
            .values(
                organization_id=self.tenant_id,
                source_type=SOURCE_SALES_INVOICE,
                source_id=invoice.id,
                customer_id=invoice.customer_id,
                amount=invoice.amount,
                outstanding=invoice.amount,
                due_date=invoice.invoice_date,
                status="open",
            )
            .on_conflict_do_nothing(index_elements=["organization_id", "source_type", "source_id"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

        receivable = await self.session.scalar(
            select(Receivable)
            .where(
                self._tenant_filter(),
                Receivable.source_type == SOURCE_SALES_INVOICE,
                Receivable.source_id == invoice.id,
            )
            .with_for_update()
        )
        if receivable is None:
            raise RuntimeError("Receivable row missing after create-or-lock.")
        return receivable

    async def get_for_invoice(self, invoice_id: UUID) -> Receivable | None:
        stmt = select(Receivable).where(
            self._tenant_filter(),
            Receivable.source_type == SOURCE_SALES_INVOICE,
            Receivable.source_id == invoice_id,
        )
        return await self.session.scalar(stmt)

    def _with_names(self):
        return (
            select(Receivable, SalesInvoice.invoice_number, Customer.name)
            .outerjoin(
                SalesInvoice,
                and_(
                    SalesInvoice.id == Receivable.source_id,
                    SalesInvoice.organization_id == self.tenant_id,
                    Receivable.source_type == SOURCE_SALES_INVOICE,
                ),
            )
            .outerjoin(
                Customer,
                and_(Customer.id == Receivable.customer_id, Customer.organization_id == self.tenant_id),
            )
        )

    async def get_by_id(self, receivable_id: UUID) -> Receivable | None:
        stmt = select(Receivable).where(Receivable.id == receivable_id, self._tenant_filter())
        return await self.session.scalar(stmt)

    async def get_with_names(
        self, receivable_id: UUID
    ) -> tuple[Receivable, str | None, str | None] | None:
        stmt = self._with_names().where(self._tenant_filter(), Receivable.id == receivable_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[Receivable, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(Receivable).where(tenant)) or 0
        stmt = (
            self._with_names()
            .where(tenant)
            .order_by(Receivable.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)
