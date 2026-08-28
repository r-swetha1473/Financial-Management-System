"""Customer persistence against customer_skg. Tenant from constructor."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.customer import Customer


class CustomerRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Customer.organization_id, self.tenant_id)

    async def list_page(self, page: int, page_size: int) -> tuple[list[Customer], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(Customer).where(tenant)) or 0
        stmt = self.scoped(
            select(Customer).order_by(Customer.created_at.desc()).offset((page - 1) * page_size).limit(page_size),
            Customer.organization_id,
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows, int(total)

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id, self._tenant_filter())
        return await self.session.scalar(stmt)

    async def create(
        self,
        *,
        name: str,
        address: str | None,
        gst_number: str | None,
        state: str | None,
        credit_limit: Decimal | None,
        phone: str | None,
        drivers_license_number: str | None,
    ) -> Customer:
        customer = Customer(
            organization_id=self.tenant_id,
            name=name,
            address=address,
            gst_number=gst_number,
            state=state,
            credit_limit=credit_limit,
            phone=phone,
            drivers_license_number=drivers_license_number,
        )
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)
        return customer
