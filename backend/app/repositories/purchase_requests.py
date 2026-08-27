"""Purchase-request persistence. Tenant from constructor; request_number from increment_sequence."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.purchase_request import PurchaseRequest
from app.models.user import User
from app.models.vendor import Vendor

PR_DOC_TYPE_PREFIX = "pr"


class PurchaseRequestRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(PurchaseRequest.organization_id, self.tenant_id)

    async def list_page(self, page: int, page_size: int) -> tuple[list[tuple[PurchaseRequest, str | None, str | None]], int]:
        tenant = self._tenant_filter()
        total = await self.session.scalar(select(func.count()).select_from(PurchaseRequest).where(tenant)) or 0
        stmt = (
            select(PurchaseRequest, Vendor.name, User.full_name)
            .outerjoin(
                Vendor,
                and_(Vendor.id == PurchaseRequest.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .outerjoin(User, User.id == PurchaseRequest.requested_by)
            .where(tenant)
            .order_by(PurchaseRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1], row[2]) for row in rows], int(total)

    async def get_by_id(self, request_id: UUID) -> tuple[PurchaseRequest, str | None, str | None] | None:
        stmt = (
            select(PurchaseRequest, Vendor.name, User.full_name)
            .outerjoin(
                Vendor,
                and_(Vendor.id == PurchaseRequest.vendor_id, Vendor.organization_id == self.tenant_id),
            )
            .outerjoin(User, User.id == PurchaseRequest.requested_by)
            .where(PurchaseRequest.id == request_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1], row[2]

    async def get_for_update(self, request_id: UUID) -> PurchaseRequest | None:
        stmt = (
            select(PurchaseRequest)
            .where(PurchaseRequest.id == request_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def _floor_year_sequence(self, year: int) -> None:
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{PR_DOC_TYPE_PREFIX}:{year}",
            table="p2p_purchase_requests",
            number_column="request_number",
            pattern=f"^PR-{year}-[0-9]+$",
        )

    async def create(
        self,
        *,
        vendor_id: UUID | None,
        requested_by: UUID,
        requested_date: date,
        notes: str | None,
        status: str,
    ) -> PurchaseRequest:
        year = requested_date.year
        await self._floor_year_sequence(year)
        nxt = await increment_sequence(self.session, self.tenant_id, f"{PR_DOC_TYPE_PREFIX}:{year}")
        request = PurchaseRequest(
            organization_id=self.tenant_id,
            vendor_id=vendor_id,
            request_number=f"PR-{year}-{nxt:03d}",
            status=status,
            requested_by=requested_by,
            requested_date=requested_date,
            notes=notes,
        )
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request
