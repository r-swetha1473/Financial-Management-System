"""Purchase-order persistence. Tenant from constructor; po_number from increment_sequence."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_request import PurchaseRequest
from app.models.vendor import Vendor

PO_DOC_TYPE_PREFIX = "po"


class PurchaseOrderRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(PurchaseOrder.organization_id, self.tenant_id)

    async def list_page(self, page: int, page_size: int) -> tuple[list[tuple[PurchaseOrder, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(PurchaseOrder).where(tenant)) or 0
        stmt = (
            select(PurchaseOrder, Vendor.name, PurchaseRequest.request_number)
            .outerjoin(
                Vendor,
                and_(Vendor.id == PurchaseOrder.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .outerjoin(
                PurchaseRequest,
                and_(
                    PurchaseRequest.id == PurchaseOrder.purchase_request_id,
                    PurchaseRequest.organization_id == self.tenant_id,
                ),
            )
            .where(tenant)
            .order_by(PurchaseOrder.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)

    async def get_by_id(self, order_id: UUID) -> tuple[PurchaseOrder, str | None, str | None] | None:
        stmt = (
            select(PurchaseOrder, Vendor.name, PurchaseRequest.request_number)
            .outerjoin(
                Vendor,
                and_(Vendor.id == PurchaseOrder.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .outerjoin(
                PurchaseRequest,
                and_(
                    PurchaseRequest.id == PurchaseOrder.purchase_request_id,
                    PurchaseRequest.organization_id == self.tenant_id,
                ),
            )
            .where(PurchaseOrder.id == order_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def get_for_update(self, order_id: UUID) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == order_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def create(
        self,
        *,
        vendor_id: UUID,
        purchase_request: PurchaseRequest | None,
        order_date: date,
        total_amount: Decimal,
        status: str,
    ) -> PurchaseOrder:
        year = order_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{PO_DOC_TYPE_PREFIX}:{year}",
            table="p2p_purchase_orders",
            number_column="po_number",
            pattern=f"^PO-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{PO_DOC_TYPE_PREFIX}:{year}")
        order = PurchaseOrder(
            organization_id=self.tenant_id,
            purchase_request_id=purchase_request.id if purchase_request is not None else None,
            vendor_id=vendor_id,
            po_number=f"PO-{year}-{nxt:03d}",
            status=status,
            order_date=order_date,
            total_amount=total_amount,
        )
        if purchase_request is not None:
            purchase_request.status = "converted"
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order
