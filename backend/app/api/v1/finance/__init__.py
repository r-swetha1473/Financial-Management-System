"""Finance API routes."""

from fastapi import APIRouter

from app.api.v1.finance import expenses, open as finance_open

router = APIRouter(prefix="/finance")
router.include_router(expenses.router)
router.include_router(finance_open.accounts_router)
router.include_router(finance_open.transactions_router)
router.include_router(finance_open.income_router)
router.include_router(finance_open.gst_router)
router.include_router(finance_open.reconciliation_router)
