"""Live report views. Purchase / Sales / Payables / Receivables / Cash Flow / GST / P&L."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.reports import ReportViewOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{key}", response_model=ApiResponse[ReportViewOut])
async def get_report(
    key: str,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[ReportViewOut]:
    return ApiResponse(data=await report_service.build(session, current.tenant_id, key))
