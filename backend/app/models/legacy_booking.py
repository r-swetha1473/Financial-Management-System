"""Legacy booking / invoice_skg / invoice_receipts. Parallel to O2C, not a replacement."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plan(Base):
    __tablename__ = "plan_skg"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Booking(Base):
    __tablename__ = "booking_skg"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    offering_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("income_offering.id"))
    customer_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("customer_skg.id"))
    booking_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    booking_end_date: Mapped[date | None] = mapped_column(Date)
    security_paid: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LegacyInvoice(Base):
    __tablename__ = "invoice_skg"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("customer_skg.id"))
    booking_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("booking_skg.id"))
    plan_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("plan_skg.id"))
    invoice_raised_date: Mapped[date] = mapped_column(Date, nullable=False)
    security_amount_deposited: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    is_gst_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceReceipt(Base):
    __tablename__ = "invoice_receipts"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    invoice_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("invoice_skg.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    pending_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_last4: Mapped[str | None] = mapped_column(String(4))
    entered_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
