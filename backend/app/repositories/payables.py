"""Payable persistence. Lock the row for money mutations; outstanding is a cache."""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.payable import Payable
from app.models.supplier_invoice import SupplierInvoice
from app.models.vendor import Vendor

SOURCE_SUPPLIER_INVOICE = "supplier_invoice"


class PayableRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Payable.organization_id, self.tenant_id)

    async def lock_or_create_for_invoice(self, invoice: SupplierInvoice) -> Payable:
        stmt = (
            pg_insert(Payable)
            .values(
                organization_id=self.tenant_id,
                source_type=SOURCE_SUPPLIER_INVOICE,
                source_id=invoice.id,
                vendor_id=invoice.vendor_id,
                amount=invoice.amount,
                outstanding=invoice.amount,
                due_date=invoice.invoice_date,
                status="open",
            )
            .on_conflict_do_nothing(index_elements=["organization_id", "source_type", "source_id"])
        )
        await self.session.execute(stmt)
        await self.session.flush()

        payable = await self.session.scalar(
            select(Payable)
            .where(
                self._tenant_filter(),
                Payable.source_type == SOURCE_SUPPLIER_INVOICE,
                Payable.source_id == invoice.id,
            )
            .with_for_update()
        )
        if payable is None:
            raise RuntimeError("Payable row missing after create-or-lock.")
        return payable

    def _with_names(self):
        return (
            select(Payable, SupplierInvoice.invoice_number, Vendor.name)
            .outerjoin(
                SupplierInvoice,
                and_(
                    SupplierInvoice.id == Payable.source_id,
                    SupplierInvoice.organization_id == self.tenant_id,
                    Payable.source_type == SOURCE_SUPPLIER_INVOICE,
                ),
            )
            .outerjoin(
                Vendor,
                and_(Vendor.id == Payable.vendor_id, Vendor.organization_id == self.tenant_id),
            )
        )

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[Payable, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(Payable).where(tenant)) or 0
        stmt = (
            self._with_names()
            .where(tenant)
            .order_by(Payable.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)

    async def get_for_invoice(self, invoice_id: UUID) -> Payable | None:
        stmt = select(Payable).where(
            self._tenant_filter(),
            Payable.source_type == SOURCE_SUPPLIER_INVOICE,
            Payable.source_id == invoice_id,
        )
        return await self.session.scalar(stmt)
