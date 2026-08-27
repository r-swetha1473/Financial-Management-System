"""Finance expense endpoints. Tenant is always the JWT organization."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Finance Expenses"])


@router.get("", response_model=PaginatedResponse[ExpenseOut])
async def list_expenses(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ExpenseOut]:
    items, total = await expense_service.list_expenses(session, current.tenant_id, page, page_size)
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/{expense_id}", response_model=ApiResponse[ExpenseOut])
async def get_expense(
    expense_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ExpenseOut]:
    record = await expense_service.get_expense(session, current.tenant_id, expense_id)
    return ApiResponse(data=record)


@router.post("", response_model=ApiResponse[ExpenseOut], status_code=201)
async def create_expense(
    payload: ExpenseCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ExpenseOut]:
    record = await expense_service.create_expense(session, current.tenant_id, current.user_id, payload)
    return ApiResponse(data=record)
