"""P2P purchase-request endpoints. Tenant is always the JWT organization. Create, get, list, approve, reject."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.purchase_request import PurchaseRequestCreate, PurchaseRequestOut
from app.services import purchase_request_service

router = APIRouter(prefix="/purchase-requests", tags=["P2P Purchase Requests"])


@router.get("", response_model=PaginatedResponse[PurchaseRequestOut])
async def list_purchase_requests(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[PurchaseRequestOut]:
    items, total = await purchase_request_service.list_purchase_requests(
        session, current.tenant_id, page, page_size
    )
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{request_id}", response_model=ApiResponse[PurchaseRequestOut])
async def get_purchase_request(
    request_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseRequestOut]:
    record = await purchase_request_service.get_purchase_request(session, current.tenant_id, request_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[PurchaseRequestOut], status_code=201)
async def create_purchase_request(
    payload: PurchaseRequestCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseRequestOut]:
    record = await purchase_request_service.create_purchase_request(
        session, current.tenant_id, current.user_id, payload
    )
    return ApiResponse(data=record)


@router.put("/{request_id}", response_model=ApiResponse[PurchaseRequestOut])
async def update_purchase_request_not_supported(
    request_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("edit"))],
) -> ApiResponse[PurchaseRequestOut]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Updating a purchase request is not supported. Approve or reject a draft or submitted request instead.",
    )


@router.patch("/{request_id}/approve", response_model=ApiResponse[PurchaseRequestOut])
async def approve_purchase_request(
    request_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseRequestOut]:
    record = await purchase_request_service.decide_purchase_request(
        session, current.tenant_id, current.user_id, request_id, "approved"
    )
    return ApiResponse(data=record)


@router.patch("/{request_id}/reject", response_model=ApiResponse[PurchaseRequestOut])
async def reject_purchase_request(
    request_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("approve"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[PurchaseRequestOut]:
    record = await purchase_request_service.decide_purchase_request(
        session, current.tenant_id, current.user_id, request_id, "rejected"
    )
    return ApiResponse(data=record)
