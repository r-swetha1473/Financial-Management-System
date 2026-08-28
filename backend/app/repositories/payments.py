"""Payment persistence. No document sequence — Angular has no payment number."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.payment import Payment
from app.models.supplier_invoice import SupplierInvoice
from app.models.vendor import Vendor

_COMPLETED = "completed"


class PaymentRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Payment.organization_id, self.tenant_id)

    def _with_names(self):
        return (
            select(Payment, SupplierInvoice.invoice_number, Vendor.id, Vendor.name)
            .join(
                SupplierInvoice,
                and_(
                    SupplierInvoice.id == Payment.supplier_invoice_id,
                    SupplierInvoice.organization_id == self.tenant_id,
                ),
            )
            .outerjoin(
                Vendor,
                and_(Vendor.id == SupplierInvoice.vendor_id, Vendor.organization_id == self.tenant_id),
            )
        )

    def _list_filters(self, search: str | None):
        clauses = [self._tenant_filter()]
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            clauses.append(
                or_(
                    SupplierInvoice.invoice_number.ilike(like),
                    Vendor.name.ilike(like),
                    Payment.payment_mode.ilike(like),
                )
            )
        return and_(*clauses)

    async def list_page(
        self, page: int, page_size: int, search: str | None = None
    ) -> tuple[list[tuple[Payment, str | None, UUID | None, str | None]], int]:
        where = self._list_filters(search)
        total = await self.session.scalar(
            select(func.count()).select_from(self._with_names().where(where).subquery())
        ) or 0
        stmt = (
            self._with_names()
            .where(where)
            .order_by(Payment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)

    async def get_with_names(
        self, payment_id: UUID
    ) -> tuple[Payment, str | None, UUID | None, str | None] | None:
        stmt = self._with_names().where(self._tenant_filter(), Payment.id == payment_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2], row[3]

    async def completed_sum_for_invoice(self, invoice_id: UUID) -> Decimal:
        paid = await self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                self._tenant_filter(),
                Payment.supplier_invoice_id == invoice_id,
                Payment.status == _COMPLETED,
            )
        )
        return Decimal(str(paid or 0))

    async def create_completed(
        self,
        *,
        supplier_invoice_id: UUID,
        payment_date: date,
        amount: Decimal,
        payment_mode: str,
    ) -> Payment:
        payment = Payment(
            organization_id=self.tenant_id,
            supplier_invoice_id=supplier_invoice_id,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_mode,
            status=_COMPLETED,
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        return payment
