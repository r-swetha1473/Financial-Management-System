"""Customer ORM model. Table remains customer_skg — do not rename."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Customer(Base):
    __tablename__ = "customer_skg"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    gst_number: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(100))
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    phone: Mapped[str | None] = mapped_column(String(50))
    drivers_license_number: Mapped[str | None] = mapped_column(String(100))
    photo_file_name: Mapped[str | None] = mapped_column(String(255))
    photo_mime_type: Mapped[str | None] = mapped_column(String(100))
    photo_file_size: Mapped[int | None] = mapped_column(BigInteger)
    photo_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    photo_document_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    address_proof_file_name: Mapped[str | None] = mapped_column(String(255))
    address_proof_mime_type: Mapped[str | None] = mapped_column(String(100))
    address_proof_file_size: Mapped[int | None] = mapped_column(BigInteger)
    address_proof_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    address_proof_document_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
