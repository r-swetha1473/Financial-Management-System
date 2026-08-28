"""O2C quotation ORM model. Table remains o2c_quotations — user-facing name is Subscribed Plan."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Quotation(Base):
    __tablename__ = "o2c_quotations"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("customer_skg.id"), nullable=False
    )
    quote_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    quote_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    valid_until: Mapped[date | None] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    plan_duration: Mapped[int | None] = mapped_column(Integer)
    billing_cycle: Mapped[str | None] = mapped_column(String(20))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
