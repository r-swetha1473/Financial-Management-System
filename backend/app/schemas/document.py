"""Document metadata schemas. No public URL — clients fetch bytes from the authenticated content route."""

from datetime import datetime

from app.schemas.common import CamelModel


class DocumentOut(CamelModel):
    id: str
    organization_id: str
    entity_name: str
    entity_id: str
    file_name: str
    mime_type: str
    file_size: int
    storage_key: str | None = None
    uploaded_by: str | None = None
    created_at: datetime
