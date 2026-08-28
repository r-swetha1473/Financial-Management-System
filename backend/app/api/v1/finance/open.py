"""Read-only finance surfaces opened in this pass: accounts, transactions, income, GST, notes."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.paging import paginated
from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.finance_open import (
    FinanceAccountOut,
    FinanceTransactionOut,
    GstSummaryOut,
    IncomeRecordOut,
    ReconciliationNoteIn,
    ReconciliationNoteOut,
)
from app.services import finance_open_service

accounts_router = APIRouter(prefix="/accounts", tags=["Finance Accounts"])
transactions_router = APIRouter(prefix="/transactions", tags=["Finance Transactions"])
income_router = APIRouter(prefix="/income", tags=["Finance Income"])
gst_router = APIRouter(prefix="/gst", tags=["Finance GST"])
reconciliation_router = APIRouter(prefix="/reconciliation", tags=["Finance Reconciliation"])


@accounts_router.get("", response_model=PaginatedResponse[FinanceAccountOut])
async def list_accounts(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await finance_open_service.list_accounts(session, current.tenant_id)
    return paginated(items, total, page, page_size)


@transactions_router.get("", response_model=PaginatedResponse[FinanceTransactionOut])
async def list_transactions(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    account_id: UUID | None = None,
    search: str = "",
):
    items, total = await finance_open_service.list_transactions(
        session, current.tenant_id, page, page_size, account_id, search
    )
    return paginated(items, total, page, page_size)


@income_router.get("", response_model=PaginatedResponse[IncomeRecordOut])
async def list_income(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await finance_open_service.list_income(session, current.tenant_id, page, page_size)
    return paginated(items, total, page, page_size)


@gst_router.get("/summary", response_model=ApiResponse[GstSummaryOut])
async def gst_summary(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = None,
    date_to: date | None = None,
):
    return ApiResponse(data=await finance_open_service.gst_summary(session, current.tenant_id, date_from, date_to))


@reconciliation_router.get("/note", response_model=ApiResponse[ReconciliationNoteOut])
async def get_note(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await finance_open_service.get_reconciliation_note(session, current.tenant_id))


@reconciliation_router.put("/note", response_model=ApiResponse[ReconciliationNoteOut])
async def save_note(
    payload: ReconciliationNoteIn,
    current: Annotated[CurrentUser, Depends(require_permission("edit"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(
        data=await finance_open_service.save_reconciliation_note(session, current.tenant_id, payload.note)
    )
