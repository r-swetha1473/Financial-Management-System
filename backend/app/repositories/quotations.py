"""Quotation persistence. Tenant from constructor; quote_number from increment_sequence as Q-{year}-{n:03d}."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.db.repository import TenantScopedRepository
from app.db.sequences import floor_year_sequence, increment_sequence
from app.db.tenant import for_tenant
from app.models.customer import Customer
from app.models.quotation import Quotation

QUOTE_DOC_TYPE_PREFIX = "q"


class QuotationRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Quotation.organization_id, self.tenant_id)

    def _list_filters(
        self,
        customer_id: UUID | None,
        status: str | None,
        search: str | None,
    ):
        clauses = [self._tenant_filter()]
        if customer_id is not None:
            clauses.append(Quotation.customer_id == customer_id)
        if status:
            clauses.append(Quotation.status == status)
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            clauses.append(or_(Quotation.quote_number.ilike(like), Customer.name.ilike(like)))
        return and_(*clauses)

    def _named_select(self):
        return select(Quotation, Customer.name).outerjoin(
            Customer,
            and_(Customer.id == Quotation.customer_id, Customer.organization_id == self.tenant_id),
        )

    async def list_page(
        self,
        page: int,
        page_size: int,
        customer_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[tuple[Quotation, str | None]], int]:
        where = self._list_filters(customer_id, status, search)
        total = await self.session.scalar(
            select(func.count()).select_from(Quotation).outerjoin(
                Customer,
                and_(Customer.id == Quotation.customer_id, Customer.organization_id == self.tenant_id),
            ).where(where)
        ) or 0
        stmt = (
            self._named_select()
            .where(where)
            .order_by(Quotation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1]) for row in rows], int(total)

    async def get_by_id(self, quotation_id: UUID) -> tuple[Quotation, str | None] | None:
        stmt = (
            select(Quotation, Customer.name)
            .outerjoin(
                Customer,
                and_(Customer.id == Quotation.customer_id, Customer.organization_id == self.tenant_id),
            )
            .where(Quotation.id == quotation_id, self._tenant_filter())
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def get_for_update(self, quotation_id: UUID) -> Quotation | None:
        stmt = (
            select(Quotation)
            .where(Quotation.id == quotation_id, self._tenant_filter())
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def create(
        self,
        *,
        customer_id: UUID,
        quote_date: date,
        valid_until: date | None,
        total_amount: Decimal,
        status: str,
        plan_duration: int | None,
        billing_cycle: str | None,
        deposit_amount: Decimal,
    ) -> Quotation:
        year = quote_date.year
        await floor_year_sequence(
            self.session,
            self.tenant_id,
            f"{QUOTE_DOC_TYPE_PREFIX}:{year}",
            table="o2c_quotations",
            number_column="quote_number",
            pattern=f"^Q-{year}-[0-9]+$",
        )
        nxt = await increment_sequence(self.session, self.tenant_id, f"{QUOTE_DOC_TYPE_PREFIX}:{year}")
        quotation = Quotation(
            organization_id=self.tenant_id,
            customer_id=customer_id,
            quote_number=f"Q-{year}-{nxt:03d}",
            status=status,
            quote_date=quote_date,
            valid_until=valid_until,
            total_amount=total_amount,
            plan_duration=plan_duration,
            billing_cycle=billing_cycle,
            deposit_amount=deposit_amount,
        )
        self.session.add(quotation)
        await self.session.commit()
        await self.session.refresh(quotation)
        return quotation
