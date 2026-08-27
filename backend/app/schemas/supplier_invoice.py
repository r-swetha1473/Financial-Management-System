"""Supplier invoice schemas. invoice_number, status, and approval_status are server-assigned on create."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class SupplierInvoiceCreate(CamelModel):
    goods_receipt_id: UUID
    vendor_id: UUID | None = None
    invoice_date: date | None = None
    amount: Decimal = Decimal("0")
    gst_amount: Decimal = Decimal("0")

    @field_validator("vendor_id", mode="before")
    @classmethod
    def empty_vendor_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("amount", "gst_amount", mode="before")
    @classmethod
    def parse_money_fields(cls, value: object) -> Decimal:
        return _parse_money(value)


class SupplierInvoiceOut(CamelModel):
    id: str
    organization_id: str
    vendor_id: str
    vendor_name: str = ""
    purchase_order_id: str | None = None
    po_number: str = ""
    goods_receipt_id: str | None = None
    grn_number: str = ""
    invoice_number: str
    status: str
    approval_status: str
    invoice_date: date
    amount: Decimal
    gst_amount: Decimal
    created_at: datetime

    @field_serializer("amount", "gst_amount")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
