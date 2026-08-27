"""Delivery persistence. Tenant from constructor; delivery_number from increment_sequence as DN-{year}-{n:03d}."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.sales_order import SalesOrder

DN_DOC_TYPE_PREFIX = "dn"


class DeliveryRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Delivery.organization_id, self.tenant_id)

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[Delivery, str | None, UUID | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(Delivery).where(tenant)) or 0
        stmt = (
            select(Delivery, SalesOrder.order_number, SalesOrder.customer_id, Customer.name)
            .outerjoin(
                SalesOrder,
                and_(SalesOrder.id == Delivery.sales_order_id, SalesOrder.organization_id == self.tenant_id),
            )
            .outerjoin(
                Customer,
                and_(Customer.id == SalesOrder.customer_id, Customer.organization_id == self.tenant_id),
            )
            .where(tenant)
            .order_by(Delivery.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    async def get_by_id(self, delivery_id: UUID) -> tuple[Delivery, str | None, UUID | None, str | None] | None:
        stmt = (
            select(Delivery, SalesOrder.order_number, SalesOrder.customer_id, Customer.name)
            .outerjoin(
                SalesOrder,
                and_(SalesOrder.id == Delivery.sales_order_id, SalesOrder.organization_id == self.tenant_id),
            )
            .outerjoin(
                Customer,
                and_(Customer.id == SalesOrder.customer_id, Customer.organization_id == self.tenant_id),
            )
            .where(Delivery.id == delivery_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def get_for_update(self, delivery_id: UUID) -> Delivery | None:
        stmt = (
            select(Delivery)
            .where(Delivery.id == delivery_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def create_against_sales_order(
        self,
        *,
        sales_order: SalesOrder,
        delivery_date: date,
        status: str,
    ) -> Delivery:
        year = delivery_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{DN_DOC_TYPE_PREFIX}:{year}",
            table="o2c_deliveries",
            number_column="delivery_number",
            pattern=f"^DN-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{DN_DOC_TYPE_PREFIX}:{year}")
        delivery = Delivery(
            organization_id=self.tenant_id,
            sales_order_id=sales_order.id,
            delivery_number=f"DN-{year}-{nxt:03d}",
            status=status,
            delivery_date=delivery_date,
        )
        if status == "delivered":
            sales_order.status = "fulfilled"
        self.session.add(delivery)
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery
