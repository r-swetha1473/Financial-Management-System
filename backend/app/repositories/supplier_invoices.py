"""Supplier-invoice persistence. Tenant from constructor; invoice_number from increment_sequence."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.goods_receipt import GoodsReceipt
from app.models.purchase_order import PurchaseOrder
from app.models.supplier_invoice import SupplierInvoice
from app.models.vendor import Vendor

SI_DOC_TYPE_PREFIX = "si"


class SupplierInvoiceRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(SupplierInvoice.organization_id, self.tenant_id)

    async def list_page(
        self, page: int, page_size: int
    ) -> tuple[list[tuple[SupplierInvoice, str | None, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(SupplierInvoice).where(tenant)) or 0
        stmt = (
            self._with_names()
            .where(tenant)
            .order_by(SupplierInvoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    def _with_names(self):
        return (
            select(SupplierInvoice, Vendor.name, PurchaseOrder.po_number, GoodsReceipt.grn_number)
            .outerjoin(
                Vendor,
                and_(Vendor.id == SupplierInvoice.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .outerjoin(
                PurchaseOrder,
                and_(
                    PurchaseOrder.id == SupplierInvoice.purchase_order_id,
                    PurchaseOrder.organization_id == self.tenant_id,
                ),
            )
            .outerjoin(
                GoodsReceipt,
                and_(
                    GoodsReceipt.id == SupplierInvoice.goods_receipt_id,
                    GoodsReceipt.organization_id == self.tenant_id,
                ),
            )
        )

    async def get_for_update(self, invoice_id: UUID) -> SupplierInvoice | None:
        stmt = (
            select(SupplierInvoice)
            .where(SupplierInvoice.id == invoice_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def get_with_names(
        self, invoice_id: UUID
    ) -> tuple[SupplierInvoice, str | None, str | None, str | None] | None:
        stmt = self._with_names().where(self._tenant_filter(), SupplierInvoice.id == invoice_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def active_for_receipt(self, goods_receipt_id: UUID) -> SupplierInvoice | None:
        stmt = (
            select(SupplierInvoice)
            .where(
                self._tenant_filter(),
                SupplierInvoice.goods_receipt_id == goods_receipt_id,
                SupplierInvoice.status != "cancelled",
            )
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def create_from_receipt(
        self,
        *,
        goods_receipt: GoodsReceipt,
        vendor_id: UUID,
        purchase_order_id: UUID | None,
        invoice_date: date,
        amount: Decimal,
        gst_amount: Decimal,
    ) -> SupplierInvoice:
        year = invoice_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{SI_DOC_TYPE_PREFIX}:{year}",
            table="p2p_supplier_invoices",
            number_column="invoice_number",
            pattern=f"^SI-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{SI_DOC_TYPE_PREFIX}:{year}")
        invoice = SupplierInvoice(
            organization_id=self.tenant_id,
            vendor_id=vendor_id,
            purchase_order_id=purchase_order_id,
            goods_receipt_id=goods_receipt.id,
            invoice_number=f"SI-{year}-{nxt:03d}",
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
