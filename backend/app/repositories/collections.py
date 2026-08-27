"""Collection persistence. No document sequence — Angular has no collection number."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.collection import Collection
from app.models.customer import Customer
from app.models.sales_invoice import SalesInvoice

_COMPLETED = "completed"


class CollectionRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Collection.organization_id, self.tenant_id)

    def _with_names(self):
        return (
            select(Collection, SalesInvoice.invoice_number, Customer.id, Customer.name)
            .join(
                SalesInvoice,
                and_(
                    SalesInvoice.id == Collection.sales_invoice_id,
                    SalesInvoice.organization_id == self.tenant_id,
                ),
            )
            .outerjoin(
                Customer,
                and_(Customer.id == SalesInvoice.customer_id, Customer.organization_id == self.tenant_id),
            )
        )

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[Collection, str | None, UUID | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(Collection).where(tenant)) or 0
        stmt = (
            self._with_names()
            .where(tenant)
            .order_by(Collection.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    async def get_with_names(
        self, collection_id: UUID
    ) -> tuple[Collection, str | None, UUID | None, str | None] | None:
        stmt = self._with_names().where(self._tenant_filter(), Collection.id == collection_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def completed_sum_for_invoice(self, invoice_id: UUID) -> Decimal:
        paid = await self.session.scalar(
            select(func.coalesce(func.sum(Collection.amount), 0)).where(
                self._tenant_filter(),
                Collection.sales_invoice_id == invoice_id,
                Collection.status == _COMPLETED,
            )
        )
        return Decimal(str(paid or 0))

    async def completed_sums_for_invoices(self, invoice_ids: list[UUID]) -> dict[UUID, Decimal]:
        if not invoice_ids:
            return {}
        stmt = (
            select(Collection.sales_invoice_id, func.coalesce(func.sum(Collection.amount), 0))
            .where(
                self._tenant_filter(),
                Collection.sales_invoice_id.in_(invoice_ids),
                Collection.status == _COMPLETED,
            )
            .group_by(Collection.sales_invoice_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {row[0]: Decimal(str(row[1] or 0)) for row in rows}

    async def create_completed(
        self,
        *,
        sales_invoice_id: UUID,
        collection_date: date,
        amount: Decimal,
        payment_mode: str,
    ) -> Collection:
        collection = Collection(
            organization_id=self.tenant_id,
            sales_invoice_id=sales_invoice_id,
            collection_date=collection_date,
            amount=amount,
            payment_mode=payment_mode,
            status=_COMPLETED,
        )
        self.session.add(collection)
        await self.session.flush()
        await self.session.refresh(collection)
        return collection
