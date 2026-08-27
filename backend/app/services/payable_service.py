"""Payable read service. Exposes the payables table; stored outstanding is a cache."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payable import Payable
from app.repositories.payables import PayableRepository
from app.schemas.payable import PayableOut


def _to_out(row: Payable, invoice_number: str | None, vendor_name: str | None) -> PayableOut:
    return PayableOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        source_type=row.source_type,
        source_id=str(row.source_id),
        invoice_number=invoice_number or "",
        vendor_id=str(row.vendor_id) if row.vendor_id else "",
        vendor_name=vendor_name or "",
        amount=row.amount,
        outstanding=row.outstanding,
        due_date=row.due_date,
        status=row.status,
        created_at=row.created_at,
    )


async def list_payables(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[PayableOut], int]:
    rows, total = await PayableRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(payable, invoice_number, vendor_name) for payable, invoice_number, vendor_name in rows], total
