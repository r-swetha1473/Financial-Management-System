"""Sales-order persistence. Tenant from constructor; order_number from increment_sequence as SO-{year}-{n:03d}."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.models.sales_order import SalesOrder

SO_DOC_TYPE_PREFIX = "so"


class SalesOrderRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(SalesOrder.organization_id, self.tenant_id)

    async def list_page(self, page: int, page_size: int) -> tuple[list[tuple[SalesOrder, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(SalesOrder).where(tenant)) or 0
        stmt = (
            select(SalesOrder, Customer.name, Quotation.quote_number)
            .outerjoin(
                Customer,
                and_(Customer.id == SalesOrder.customer_id, Customer.organization_id == self.tenant_id),
            )
            .outerjoin(
                Quotation,
                and_(Quotation.id == SalesOrder.quotation_id, Quotation.organization_id == self.tenant_id),
            )
            .where(tenant)
            .order_by(SalesOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)

    async def get_by_id(self, order_id: UUID) -> tuple[SalesOrder, str | None, str | None] | None:
        stmt = (
            select(SalesOrder, Customer.name, Quotation.quote_number)
            .outerjoin(
                Customer,
                and_(Customer.id == SalesOrder.customer_id, Customer.organization_id == self.tenant_id),
            )
            .outerjoin(
                Quotation,
                and_(Quotation.id == SalesOrder.quotation_id, Quotation.organization_id == self.tenant_id),
            )
            .where(SalesOrder.id == order_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def get_for_update(self, order_id: UUID) -> SalesOrder | None:
        stmt = (
            select(SalesOrder)
            .where(SalesOrder.id == order_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def create(
        self,
        *,
        customer_id: UUID,
        quotation: Quotation | None,
        order_date: date,
        total_amount: Decimal,
        status: str,
    ) -> SalesOrder:
        year = order_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{SO_DOC_TYPE_PREFIX}:{year}",
            table="o2c_sales_orders",
            number_column="order_number",
            pattern=f"^SO-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{SO_DOC_TYPE_PREFIX}:{year}")
        order = SalesOrder(
            organization_id=self.tenant_id,
            customer_id=customer_id,
            quotation_id=quotation.id if quotation is not None else None,
            order_number=f"SO-{year}-{nxt:03d}",
            status=status,
            order_date=order_date,
            total_amount=total_amount,
        )
        if quotation is not None:
            quotation.status = "converted"
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order
