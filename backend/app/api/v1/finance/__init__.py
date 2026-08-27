"""Finance API routes."""

from fastapi import APIRouter

from app.api.v1.finance import expenses

router = APIRouter(prefix="/finance")
router.include_router(expenses.router)
