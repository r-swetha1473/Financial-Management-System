"""Reference-data create/list."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.repositories.finance_open import ReferenceDataRepository
from app.schemas.reports import ReferenceCreate, ReferenceOut


def _out(row) -> ReferenceOut:
    return ReferenceOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        data_type=row.data_type,
        code=row.code,
        label=row.label,
        is_active=row.is_active,
        created_at=row.created_at,
    )


async def list_reference(session, tenant_id, page, page_size, search: str):
    rows, total = await ReferenceDataRepository(session, tenant_id).list_page(page, page_size, search)
    return [_out(row) for row in rows], total


async def create_reference(session, tenant_id, payload: ReferenceCreate) -> ReferenceOut:
    try:
        row = await ReferenceDataRepository(session, tenant_id).create(
            data_type=payload.data_type.strip(),
            code=payload.code.strip(),
            label=payload.label.strip(),
            is_active=payload.is_active,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reference row with this type and code already exists.",
        ) from exc
    return _out(row)
