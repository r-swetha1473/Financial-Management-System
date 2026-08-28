"""Reference-data create/list. Updates are out of scope."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.paging import paginated
from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.reports import ReferenceCreate, ReferenceOut
from app.services import reference_data_service

router = APIRouter(prefix="/reference-data", tags=["Reference Data"])


@router.get("", response_model=PaginatedResponse[ReferenceOut])
async def list_reference(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str = "",
):
    items, total = await reference_data_service.list_reference(session, current.tenant_id, page, page_size, search)
    return paginated(items, total, page, page_size)


@router.post("", response_model=ApiResponse[ReferenceOut], status_code=201)
async def create_reference(
    payload: ReferenceCreate,
    current: Annotated[CurrentUser, Depends(require_permission("maintain_reference"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await reference_data_service.create_reference(session, current.tenant_id, payload))
