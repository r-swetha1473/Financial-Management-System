"""Sales-invoice persistence. Tenant from constructor; invoice_number from increment_sequence as O2C-{year}-{n:04d}."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.sales_invoice import SalesInvoice
from app.models.sales_order import SalesOrder

O2C_DOC_TYPE_PREFIX = "o2c"


class SalesInvoiceRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(SalesInvoice.organization_id, self.tenant_id)

    def _with_names(self):
        return (
            select(SalesInvoice, Customer.name, SalesOrder.order_number, Delivery.delivery_number)
            .outerjoin(
                Customer,
                and_(Customer.id == SalesInvoice.customer_id, Customer.organization_id == self.tenant_id),
            )
            .outerjoin(
                SalesOrder,
                and_(
                    SalesOrder.id == SalesInvoice.sales_order_id,
                    SalesOrder.organization_id == self.tenant_id,
                ),
            )
            .outerjoin(
                Delivery,
                and_(
                    Delivery.id == SalesInvoice.delivery_id,
                    Delivery.organization_id == self.tenant_id,
                ),
            )
        )

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[SalesInvoice, str | None, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(SalesInvoice).where(tenant)) or 0
        stmt = (
            self._with_names()
            .where(tenant)
            .order_by(SalesInvoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    async def get_for_update(self, invoice_id: UUID) -> SalesInvoice | None:
        stmt = (
            select(SalesInvoice)
            .where(SalesInvoice.id == invoice_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def get_with_names(
        self, invoice_id: UUID
    ) -> tuple[SalesInvoice, str | None, str | None, str | None] | None:
        stmt = self._with_names().where(self._tenant_filter(), SalesInvoice.id == invoice_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def active_for_delivery(self, delivery_id: UUID) -> SalesInvoice | None:
        stmt = (
            select(SalesInvoice)
            .where(
                self._tenant_filter(),
                SalesInvoice.delivery_id == delivery_id,
                SalesInvoice.status != "cancelled",
            )
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def create_from_delivery(
        self,
        *,
        delivery: Delivery,
        customer_id: UUID,
        sales_order_id: UUID | None,
        invoice_date: date,
        amount: Decimal,
        gst_amount: Decimal,
    ) -> SalesInvoice:
        year = invoice_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{O2C_DOC_TYPE_PREFIX}:{year}",
            table="o2c_sales_invoices",
            number_column="invoice_number",
            pattern=f"^O2C-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{O2C_DOC_TYPE_PREFIX}:{year}")
        invoice = SalesInvoice(
            organization_id=self.tenant_id,
            customer_id=customer_id,
            sales_order_id=sales_order_id,
            delivery_id=delivery.id,
            invoice_number=f"O2C-{year}-{nxt:04d}",
            status="pending",
            approval_status="pending",
            invoice_date=invoice_date,
            amount=amount,
            gst_amount=gst_amount,
        )
        self.session.add(invoice)
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice
