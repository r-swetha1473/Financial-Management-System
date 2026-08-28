"""Goods-receipt persistence. Tenant from constructor; grn_number from increment_sequence."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.goods_receipt import GoodsReceipt
from app.models.purchase_order import PurchaseOrder
from app.models.vendor import Vendor

GRN_DOC_TYPE_PREFIX = "grn"


class GoodsReceiptRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(GoodsReceipt.organization_id, self.tenant_id)

    def _po_join(self):
        return and_(
            PurchaseOrder.id == GoodsReceipt.purchase_order_id,
            PurchaseOrder.organization_id == self.tenant_id,
        )

    def _vendor_join(self):
        return and_(Vendor.id == PurchaseOrder.vendor_id, Vendor.organization_id == self.tenant_id)

    def _list_filters(self, status: str | None, search: str | None):
        clauses = [self._tenant_filter()]
        if status:
            clauses.append(GoodsReceipt.status == status)
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            clauses.append(
                or_(
                    GoodsReceipt.grn_number.ilike(like),
                    PurchaseOrder.po_number.ilike(like),
                    Vendor.name.ilike(like),
                )
            )
        return and_(*clauses)

    async def list_page(
        self, page: int, page_size: int, status: str | None = None, search: str | None = None
    ) -> tuple[list[tuple[GoodsReceipt, str | None, UUID | None, str | None]], int]:
        where = self._list_filters(status, search)
        total = await self.session.scalar(
            select(func.count())
            .select_from(GoodsReceipt)
            .outerjoin(PurchaseOrder, self._po_join())
            .outerjoin(Vendor, self._vendor_join())
            .where(where)
        ) or 0
        stmt = (
            select(GoodsReceipt, PurchaseOrder.po_number, PurchaseOrder.vendor_id, Vendor.name)
            .outerjoin(PurchaseOrder, self._po_join())
            .outerjoin(Vendor, self._vendor_join())
            .where(where)
            .order_by(GoodsReceipt.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    async def get_by_id(
        self, receipt_id: UUID
    ) -> tuple[GoodsReceipt, str | None, UUID | None, str | None] | None:
        stmt = (
            select(GoodsReceipt, PurchaseOrder.po_number, PurchaseOrder.vendor_id, Vendor.name)
            .outerjoin(
                PurchaseOrder,
                and_(
                    PurchaseOrder.id == GoodsReceipt.purchase_order_id,
                    PurchaseOrder.organization_id == self.tenant_id,
                ),
            )
            .outerjoin(
                Vendor,
                and_(Vendor.id == PurchaseOrder.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .where(GoodsReceipt.id == receipt_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def get_for_update(self, receipt_id: UUID) -> GoodsReceipt | None:
        stmt = (
            select(GoodsReceipt)
            .where(GoodsReceipt.id == receipt_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def create_against_issued_order(
        self,
        *,
        purchase_order: PurchaseOrder,
        receipt_date: date,
        status: str,
    ) -> GoodsReceipt:
        year = receipt_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{GRN_DOC_TYPE_PREFIX}:{year}",
            table="p2p_goods_receipts",
            number_column="grn_number",
            pattern=f"^GRN-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{GRN_DOC_TYPE_PREFIX}:{year}")
        receipt = GoodsReceipt(
            organization_id=self.tenant_id,
            purchase_order_id=purchase_order.id,
            grn_number=f"GRN-{year}-{nxt:03d}",
            status=status,
            receipt_date=receipt_date,
        )
        if status == "received":
            purchase_order.status = "received"
        self.session.add(receipt)
        await self.session.commit()
        await self.session.refresh(receipt)
        return receipt
