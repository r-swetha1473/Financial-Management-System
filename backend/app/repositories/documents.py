"""Document persistence. Every query is tenant-scoped; file_data is only loaded for download."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import undefer

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.document import Document


class DocumentRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(Document.organization_id, self.tenant_id)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        stmt = select(Document).where(Document.id == document_id, self._tenant_filter())
        return await self.session.scalar(stmt)

    async def get_content(self, document_id: UUID) -> Document | None:
        stmt = (
            select(Document)
            .options(undefer(Document.file_data))
            .where(Document.id == document_id, self._tenant_filter())
        )
        return await self.session.scalar(stmt)

    async def add(
        self,
        *,
        document_id: UUID,
        entity_name: str,
        entity_id: UUID,
        file_name: str,
        mime_type: str,
        file_size: int,
        storage_key: str,
        file_data: bytes,
        uploaded_by: UUID | None,
    ) -> Document:
        document = Document(
            id=document_id,
            organization_id=self.tenant_id,
            entity_name=entity_name,
            entity_id=entity_id,
            file_name=file_name,
            mime_type=mime_type,
            file_size=file_size,
            storage_key=storage_key,
            file_data=file_data,
            uploaded_by=uploaded_by,
        )
        self.session.add(document)
        await self.session.flush()
        return document
