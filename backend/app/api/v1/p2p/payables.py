"""P2P payable endpoints. Read-only; rows are created by payments."""

from math import ceil
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.payable import PayableOut
from app.services import payable_service

router = APIRouter(prefix="/payables", tags=["P2P Payables"])


@router.get("", response_model=PaginatedResponse[PayableOut])
async def list_payables(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    vendor_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[Literal["open", "partial", "closed"] | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[PayableOut]:
    items, total = await payable_service.list_payables(
        session,
        current.tenant_id,
        page,
        page_size,
        vendor_id=vendor_id,
        status=status,
        search=search,
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )
