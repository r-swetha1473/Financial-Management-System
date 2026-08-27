"""O2C sales-invoice ORM model."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SalesInvoice(Base):
    __tablename__ = "o2c_sales_invoices"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("customer_skg.id"), nullable=False
    )
    sales_order_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("o2c_sales_orders.id")
    )
    delivery_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("o2c_deliveries.id")
    )
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
