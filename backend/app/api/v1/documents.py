"""Authenticated document upload and download. No public URLs; ownership is re-checked on every fetch."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.paging import paginated
from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.document import DocumentOut
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


def _content_disposition(file_name: str) -> str:
    safe = file_name.replace("\\", "_").replace('"', "")
    return f'inline; filename="{safe}"'


@router.get("", response_model=PaginatedResponse[DocumentOut])
async def list_documents(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str = "",
) -> PaginatedResponse[DocumentOut]:
    items, total = await document_service.list_documents(session, current.tenant_id, page, page_size, search)
    return paginated(items, total, page, page_size)


@router.post("", response_model=ApiResponse[DocumentOut], status_code=201)
async def upload_document(
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    entityName: Annotated[str, Form()],
    entityId: Annotated[UUID, Form()],
    kind: Annotated[str | None, Form()] = None,
) -> ApiResponse[DocumentOut]:
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    document = await document_service.store_bytes(
        session,
        current.tenant_id,
        current.user_id,
        entity_name=entityName,
        entity_id=entityId,
        file_name=file.filename or "upload",
        mime_type=mime,
        data=data,
        kind=kind,
    )
    return ApiResponse(data=document_service.to_out(document))


@router.get("/{document_id}", response_model=ApiResponse[DocumentOut])
async def get_document(
    document_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[DocumentOut]:
    document = await document_service.get_document(session, current.tenant_id, document_id)
    return ApiResponse(data=document)


@router.get("/{document_id}/content")
async def download_document(
    document_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    document = await document_service.get_content(session, current.tenant_id, document_id)
    return Response(
        content=document.file_data,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": _content_disposition(document.file_name),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
