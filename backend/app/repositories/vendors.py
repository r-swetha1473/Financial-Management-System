"""Vendor persistence. Tenant is injected at construction; never taken from a payload."""

from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.vendor import Vendor


class VendorRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Vendor.organization_id, self.tenant_id)

    def _list_filters(self, status: str | None, search: str | None):
        clauses = [self._tenant_filter()]
        if status:
            clauses.append(Vendor.status == status)
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            clauses.append(or_(Vendor.name.ilike(like), Vendor.email.ilike(like), Vendor.gst_number.ilike(like)))
        return and_(*clauses)

    async def list_page(
        self, page: int, page_size: int, status: str | None = None, search: str | None = None
    ) -> tuple[list[Vendor], int]:
        where = self._list_filters(status, search)
        total = await self.session.scalar(select(func.count()).select_from(Vendor).where(where)) or 0
        stmt = select(Vendor).where(where).order_by(Vendor.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, int(total)

    async def get_by_id(self, vendor_id: UUID) -> Vendor | None:
        stmt = select(Vendor).where(Vendor.id == vendor_id, self._tenant_filter())
        return await self.session.scalar(stmt)

    async def create(
        self,
        *,
        name: str,
        address: str | None,
        phone: str | None,
        email: str | None,
        poc_name: str | None,
        poc_email: str | None,
        gst_number: str | None,
        state: str | None,
        status: str,
    ) -> Vendor:
        vendor = Vendor(
            organization_id=self.tenant_id,
            name=name,
            address=address,
            phone=phone,
            email=email,
            poc_name=poc_name,
            poc_email=poc_email,
            gst_number=gst_number,
            state=state,
            status=status,
        )
        self.session.add(vendor)
        await self.session.commit()
        await self.session.refresh(vendor)
        return vendor
