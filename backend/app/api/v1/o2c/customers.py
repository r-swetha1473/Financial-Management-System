"""O2C customer endpoints. Persist to customer_skg; tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.customer import CustomerCreate, CustomerOut
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["O2C Customers"])


@router.get("", response_model=PaginatedResponse[CustomerOut])
async def list_customers(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[CustomerOut]:
    items, total = await customer_service.list_customers(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{customer_id}", response_model=ApiResponse[CustomerOut])
async def get_customer(
    customer_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CustomerOut]:
    customer = await customer_service.get_customer(session, current.tenant_id, customer_id)
    return ApiResponse(data=customer)


@router.post("", response_model=ApiResponse[CustomerOut], status_code=201)
async def create_customer(
    payload: CustomerCreate,
    current: Annotated[CurrentUser, Depends(require_permission("maintain_reference"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[CustomerOut]:
    customer = await customer_service.create_customer(session, current.tenant_id, payload)
    return ApiResponse(data=customer)
