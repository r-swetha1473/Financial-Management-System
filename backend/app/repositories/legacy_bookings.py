"""Legacy booking / invoice_skg / receipt persistence."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.catalog import Offering
from app.models.customer import Customer
from app.models.legacy_booking import Booking, InvoiceReceipt, LegacyInvoice
from app.models.user import User


class LegacyBookingRepository(TenantScopedRepository):
    def _tenant(self, model):
        return for_tenant(model.organization_id, self.tenant_id)

    async def list_bookings(self, page: int, page_size: int, customer_id: UUID | None) -> tuple[list[tuple], int]:
        tenant = self._tenant(Booking)
        filters = [tenant]
        if customer_id:
            filters.append(Booking.customer_id == customer_id)
        total = await self.session.scalar(select(func.count()).select_from(Booking).where(*filters)) or 0
        stmt = (
            select(Booking, Customer.name, Offering.name)
            .outerjoin(Customer, Customer.id == Booking.customer_id)
            .outerjoin(Offering, Offering.id == Booking.offering_id)
            .where(*filters)
            .order_by(Booking.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).all()), int(total)

    async def get_booking_named(self, booking_id: UUID):
        stmt = (
            select(Booking, Customer.name, Offering.name)
            .outerjoin(Customer, Customer.id == Booking.customer_id)
            .outerjoin(Offering, Offering.id == Booking.offering_id)
            .where(Booking.id == booking_id, self._tenant(Booking))
        )
        return (await self.session.execute(stmt)).one_or_none()

    async def create_booking(self, **kwargs) -> Booking:
        row = Booking(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def list_invoices(self, page: int, page_size: int, customer_id: UUID | None) -> tuple[list[tuple], int]:
        tenant = self._tenant(LegacyInvoice)
        filters = [tenant]
        if customer_id:
            filters.append(LegacyInvoice.customer_id == customer_id)
        total = await self.session.scalar(select(func.count()).select_from(LegacyInvoice).where(*filters)) or 0
        paid = (
            select(InvoiceReceipt.invoice_id, func.coalesce(func.sum(InvoiceReceipt.receipt_amount), 0).label("paid"))
            .where(self._tenant(InvoiceReceipt))
            .group_by(InvoiceReceipt.invoice_id)
            .subquery()
        )
        stmt = (
            select(LegacyInvoice, Customer.name, Booking.id, Offering.name, func.coalesce(paid.c.paid, 0))
            .outerjoin(Customer, Customer.id == LegacyInvoice.customer_id)
            .outerjoin(Booking, Booking.id == LegacyInvoice.booking_id)
            .outerjoin(Offering, Offering.id == Booking.offering_id)
            .outerjoin(paid, paid.c.invoice_id == LegacyInvoice.id)
            .where(*filters)
            .order_by(LegacyInvoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).all()), int(total)

    async def get_invoice_named(self, invoice_id: UUID):
        stmt = (
            select(LegacyInvoice, Customer.name, Offering.name)
            .outerjoin(Customer, Customer.id == LegacyInvoice.customer_id)
            .outerjoin(Booking, Booking.id == LegacyInvoice.booking_id)
            .outerjoin(Offering, Offering.id == Booking.offering_id)
            .where(LegacyInvoice.id == invoice_id, self._tenant(LegacyInvoice))
        )
        return (await self.session.execute(stmt)).one_or_none()

    async def get_invoice(self, invoice_id: UUID) -> LegacyInvoice | None:
        return await self.session.scalar(
            select(LegacyInvoice).where(LegacyInvoice.id == invoice_id, self._tenant(LegacyInvoice))
        )

    async def next_invoice_number(self) -> str:
        year = date.today().year
        prefix = f"INV-{year}-"
        stmt = select(func.count()).select_from(LegacyInvoice).where(
            self._tenant(LegacyInvoice), LegacyInvoice.invoice_number.like(f"{prefix}%")
        )
        n = int(await self.session.scalar(stmt) or 0) + 1
        return f"{prefix}{n:04d}"

    async def create_invoice(self, **kwargs) -> LegacyInvoice:
        row = LegacyInvoice(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def paid_on_invoice(self, invoice_id: UUID) -> Decimal:
        value = await self.session.scalar(
            select(func.coalesce(func.sum(InvoiceReceipt.receipt_amount), 0)).where(
                InvoiceReceipt.invoice_id == invoice_id, self._tenant(InvoiceReceipt)
            )
        )
        return Decimal(str(value or 0))

    async def list_receipts(self, page: int, page_size: int) -> tuple[list[tuple], int]:
        tenant = self._tenant(InvoiceReceipt)
        total = await self.session.scalar(select(func.count()).select_from(InvoiceReceipt).where(tenant)) or 0
        stmt = (
            select(InvoiceReceipt, LegacyInvoice.invoice_number, User.full_name)
            .join(LegacyInvoice, LegacyInvoice.id == InvoiceReceipt.invoice_id)
            .outerjoin(User, User.id == InvoiceReceipt.entered_by)
            .where(tenant)
            .order_by(InvoiceReceipt.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(stmt)).all()), int(total)

    async def get_receipt_named(self, receipt_id: UUID):
        stmt = (
            select(InvoiceReceipt, LegacyInvoice.invoice_number, User.full_name)
            .join(LegacyInvoice, LegacyInvoice.id == InvoiceReceipt.invoice_id)
            .outerjoin(User, User.id == InvoiceReceipt.entered_by)
            .where(InvoiceReceipt.id == receipt_id, self._tenant(InvoiceReceipt))
        )
        return (await self.session.execute(stmt)).one_or_none()

    async def create_receipt(self, **kwargs) -> InvoiceReceipt:
        row = InvoiceReceipt(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
