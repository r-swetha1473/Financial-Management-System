"""P2P vendor endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.vendor import VendorCreate, VendorOut
from app.services import vendor_service

router = APIRouter(prefix="/vendors", tags=["P2P Vendors"])


@router.get("", response_model=PaginatedResponse[VendorOut])
async def list_vendors(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[VendorOut]:
    items, total = await vendor_service.list_vendors(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{vendor_id}", response_model=ApiResponse[VendorOut])
async def get_vendor(
    vendor_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[VendorOut]:
    vendor = await vendor_service.get_vendor(session, current.tenant_id, vendor_id)
    return ApiResponse(data=vendor)


@router.post("", response_model=ApiResponse[VendorOut], status_code=201)
async def create_vendor(
    payload: VendorCreate,
    current: Annotated[CurrentUser, Depends(require_permission("maintain_reference"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[VendorOut]:
    vendor = await vendor_service.create_vendor(session, current.tenant_id, payload)
    return ApiResponse(data=vendor)
