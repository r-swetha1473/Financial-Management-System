"""Dashboard API routes. Cash position and summary money fields are live org-scoped aggregates."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    CashPositionItem,
    DashboardCategoryBreakdown,
    DashboardSummary,
    DashboardTrendPoint,
    ProductFinancialSummary,
    RecentExpenseRow,
    RecentInvoiceRow,
    RecentReceiptRow,
)
from app.services import cash_position_service, dev_seed

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/summary", response_model=ApiResponse[DashboardSummary])
async def dashboard_summary(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DashboardSummary]:
    snapshot = await cash_position_service.compute(session, current.tenant_id)
    return ApiResponse(data=cash_position_service.to_summary(snapshot))


@router.get("/expenses", response_model=ApiResponse[list[RecentExpenseRow]])
async def dashboard_expenses() -> ApiResponse[list[RecentExpenseRow]]:
    return ApiResponse(data=dev_seed.get_recent_expenses())


@router.get("/income", response_model=ApiResponse[list[DashboardTrendPoint]])
async def dashboard_income(
    period: str = Query(default="monthly", pattern="^(daily|weekly|monthly)$"),
) -> ApiResponse[list[DashboardTrendPoint]]:
    return ApiResponse(data=dev_seed.get_income_expense_trend(period))


@router.get("/cash-position", response_model=ApiResponse[list[CashPositionItem]])
async def dashboard_cash_position(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[CashPositionItem]]:
    snapshot = await cash_position_service.compute(session, current.tenant_id)
    return ApiResponse(data=cash_position_service.to_items(snapshot))


@router.get("/categories", response_model=ApiResponse[list[DashboardCategoryBreakdown]])
async def dashboard_categories() -> ApiResponse[list[DashboardCategoryBreakdown]]:
    return ApiResponse(data=dev_seed.get_expense_categories())


@router.get("/invoices", response_model=ApiResponse[list[RecentInvoiceRow]])
async def dashboard_invoices() -> ApiResponse[list[RecentInvoiceRow]]:
    return ApiResponse(data=dev_seed.get_recent_invoices())


@router.get("/receipts", response_model=ApiResponse[list[RecentReceiptRow]])
async def dashboard_receipts() -> ApiResponse[list[RecentReceiptRow]]:
    return ApiResponse(data=dev_seed.get_recent_receipts())


@router.get("/products", response_model=ApiResponse[list[ProductFinancialSummary]])
async def dashboard_products() -> ApiResponse[list[ProductFinancialSummary]]:
    return ApiResponse(data=dev_seed.get_product_summaries())


@router.get("/product/{product_id}", response_model=ApiResponse[ProductFinancialSummary])
async def dashboard_product(product_id: str) -> ApiResponse[ProductFinancialSummary]:
    summaries = dev_seed.get_product_summaries()
    match = next((item for item in summaries if item.product_id == product_id), summaries[0])
    return ApiResponse(data=match)
