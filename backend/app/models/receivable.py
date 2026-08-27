"""Receivable ORM model. outstanding is a cache; live compute is source of truth."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Receivable(Base):
    __tablename__ = "receivables"
    __table_args__ = (
        UniqueConstraint("organization_id", "source_type", "source_id", name="receivables_org_source_uidx"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("customer_skg.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    outstanding: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
