"""Minimal document storage. storage_key is an ownership path, never a public URL.

Download always re-checks organization_id from the JWT. No folders, versions, or sharing.
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.document import Document
from app.repositories.customers import CustomerRepository
from app.repositories.documents import DocumentRepository
from app.repositories.finance_open import DocumentListRepository
from app.schemas.document import DocumentOut

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_ENTITY_NAME = re.compile(r"^[a-z][a-z0-9_.-]{0,99}$")
_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_IMAGE_MIMES = {"image/jpeg", "image/png"}
_ALLOWED_MIMES = _IMAGE_MIMES | {"application/pdf"}
_MIME_ALIASES = {"image/jpg": "image/jpeg"}
_EXT_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}
_CUSTOMER_KINDS = {"photo", "address_proof"}


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=str(document.id),
        organization_id=str(document.organization_id),
        entity_name=document.entity_name,
        entity_id=str(document.entity_id),
        file_name=document.file_name,
        mime_type=document.mime_type,
        file_size=int(document.file_size),
        storage_key=document.storage_key,
        uploaded_by=str(document.uploaded_by) if document.uploaded_by else None,
        created_at=document.created_at,
    )


def safe_filename(name: str) -> str:
    base = Path(name or "").name.strip() or "upload"
    cleaned = _UNSAFE_FILENAME.sub("_", base).strip("._") or "upload"
    return cleaned[:180]


def make_storage_key(
    organization_id: UUID,
    entity_name: str,
    entity_id: UUID,
    kind: str | None,
    document_id: UUID,
    file_name: str,
) -> str:
    parts = [str(organization_id), entity_name, str(entity_id)]
    if kind:
        parts.append(kind)
    parts.append(f"{document_id}-{file_name}")
    return "/".join(parts)[:512]


def _normalize_entity_name(value: str) -> str:
    name = (value or "").strip().lower()
    if not _ENTITY_NAME.fullmatch(name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_name must be a lowercase identifier.",
        )
    return name


def _normalize_kind(kind: str | None) -> str | None:
    if kind is None:
        return None
    value = kind.strip().lower()
    if not value:
        return None
    if value not in _CUSTOMER_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="kind must be photo or address_proof.",
        )
    return value


def _validate_mime(mime_type: str, file_name: str, kind: str | None) -> str:
    mime = (mime_type or "").split(";")[0].strip().lower()
    mime = _MIME_ALIASES.get(mime, mime)
    ext = Path(file_name or "").suffix.lower()
    if mime in ("", "application/octet-stream") and ext in _EXT_MIME:
        mime = _EXT_MIME[ext]
    if kind == "photo":
        allowed_mimes = _IMAGE_MIMES
        allowed_exts = {".png", ".jpg", ".jpeg"}
        message = "Customer photo must be a PNG or JPEG image."
    else:
        allowed_mimes = _ALLOWED_MIMES
        allowed_exts = {".png", ".jpg", ".jpeg", ".pdf"}
        message = "File must be a PNG, JPEG, or PDF."
    if mime not in allowed_mimes or (ext and ext not in allowed_exts):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    return mime


def _validate_bytes(data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File content is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be 10 MB or smaller.",
        )


async def _link_customer_document(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    kind: str,
    document_id: UUID,
    file_name: str,
    mime_type: str,
    file_size: int,
) -> None:
    customer = await CustomerRepository(session, tenant_id).get_by_id(customer_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found in this organization.",
        )
    if kind == "photo":
        customer.photo_document_id = document_id
        customer.photo_file_name = file_name
        customer.photo_mime_type = mime_type
        customer.photo_file_size = file_size
    else:
        customer.address_proof_document_id = document_id
        customer.address_proof_file_name = file_name
        customer.address_proof_mime_type = mime_type
        customer.address_proof_file_size = file_size


async def store_bytes(
    session: AsyncSession,
    tenant_id: UUID,
    uploaded_by: UUID | None,
    *,
    entity_name: str,
    entity_id: UUID,
    file_name: str,
    mime_type: str,
    data: bytes,
    kind: str | None = None,
    commit: bool = True,
) -> Document:
    name = _normalize_entity_name(entity_name)
    normalized_kind = _normalize_kind(kind)
    mime = _validate_mime(mime_type, file_name, normalized_kind)
    _validate_bytes(data)
    safe_name = safe_filename(file_name)

    if name == "customer":
        customer = await session.get(Customer, entity_id)
        if customer is None or customer.organization_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found in this organization.",
            )
        if normalized_kind is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Customer uploads require kind photo or address_proof.",
            )

    document_id = uuid4()
    storage_key = make_storage_key(tenant_id, name, entity_id, normalized_kind, document_id, safe_name)
    document = await DocumentRepository(session, tenant_id).add(
        document_id=document_id,
        entity_name=name,
        entity_id=entity_id,
        file_name=safe_name,
        mime_type=mime,
        file_size=len(data),
        storage_key=storage_key,
        file_data=data,
        uploaded_by=uploaded_by,
    )
    if name == "customer" and normalized_kind in _CUSTOMER_KINDS:
        await _link_customer_document(
            session,
            tenant_id,
            entity_id,
            normalized_kind,
            document.id,
            safe_name,
            mime,
            len(data),
        )
    if commit:
        await session.commit()
        await session.refresh(document)
    return document


async def list_documents(session: AsyncSession, tenant_id: UUID, page: int, page_size: int, search: str = ""):
    rows, total = await DocumentListRepository(session, tenant_id).list_page(page, page_size, search)
    return [_to_out(row) for row in rows], total


async def get_document(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> DocumentOut:
    document = await DocumentRepository(session, tenant_id).get_by_id(document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this organization.",
        )
    return _to_out(document)


async def get_content(session: AsyncSession, tenant_id: UUID, document_id: UUID) -> Document:
    document = await DocumentRepository(session, tenant_id).get_content(document_id)
    if document is None or document.file_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this organization.",
        )
    return document


def to_out(document: Document) -> DocumentOut:
    return _to_out(document)
