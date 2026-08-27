"""Purchase order ORM model."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PurchaseOrder(Base):
    __tablename__ = "p2p_purchase_orders"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    purchase_request_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("p2p_purchase_requests.id")
    )
    vendor_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    po_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    order_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    total_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
