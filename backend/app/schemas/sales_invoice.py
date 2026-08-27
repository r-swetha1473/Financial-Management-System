"""Sales invoice schemas. invoice_number, status, and approval_status are server-assigned on create."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class SalesInvoiceCreate(CamelModel):
    delivery_id: UUID
    customer_id: UUID | None = None
    sales_order_id: UUID | None = None
    invoice_date: date | None = None
    amount: Decimal = Decimal("0")
    gst_amount: Decimal = Decimal("0")

    @field_validator("customer_id", "sales_order_id", mode="before")
    @classmethod
    def empty_fk_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("amount", "gst_amount", mode="before")
    @classmethod
    def parse_money_fields(cls, value: object) -> Decimal:
        return _parse_money(value)


class SalesInvoiceOut(CamelModel):
    id: str
    organization_id: str
    customer_id: str
    customer_name: str = ""
    sales_order_id: str | None = None
    order_number: str = ""
    delivery_id: str | None = None
    delivery_number: str = ""
    invoice_number: str
    status: str
    approval_status: str
    invoice_date: date
    amount: Decimal
    gst_amount: Decimal
    outstanding: Decimal
    created_at: datetime

    @field_serializer("amount", "gst_amount", "outstanding")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
