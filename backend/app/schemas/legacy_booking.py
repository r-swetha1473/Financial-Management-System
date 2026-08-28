"""Legacy booking / invoice_skg / receipt schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from app.schemas.common import CamelModel


def _money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _empty_uuid(value: object) -> object:
    if value == "":
        return None
    return value


class BookingCreate(CamelModel):
    offering_id: UUID | None = None
    customer_id: UUID
    booking_start_date: date
    booking_end_date: date | None = None
    security_paid: Decimal = Decimal("0")

    @field_validator("offering_id", mode="before")
    @classmethod
    def empty_offering(cls, value: object) -> object:
        return _empty_uuid(value)

    @field_validator("security_paid", mode="before")
    @classmethod
    def parse_security(cls, value: object) -> Decimal:
        return _money(value)


class BookingOut(CamelModel):
    id: str
    organization_id: str
    offering_id: str | None = None
    offering_name: str = ""
    customer_id: str | None = None
    customer_name: str = ""
    booking_start_date: date
    booking_end_date: date | None = None
    security_paid: Decimal
    created_at: datetime

    @field_serializer("security_paid")
    def serialize_security(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class LegacyInvoiceCreate(CamelModel):
    invoice_number: str | None = Field(default=None, max_length=100)
    customer_id: UUID | None = None
    booking_id: UUID | None = None
    plan_id: UUID | None = None
    invoice_raised_date: date
    security_amount_deposited: Decimal = Decimal("0")
    invoice_amount: Decimal
    is_gst_invoice: bool = False
    gst_amount: Decimal = Decimal("0")

    @field_validator("customer_id", "booking_id", "plan_id", mode="before")
    @classmethod
    def empty_fk(cls, value: object) -> object:
        return _empty_uuid(value)

    @field_validator("invoice_number", mode="before")
    @classmethod
    def blank_number(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("security_amount_deposited", "invoice_amount", "gst_amount", mode="before")
    @classmethod
    def parse_amounts(cls, value: object) -> Decimal:
        return _money(value)


class LegacyInvoiceOut(CamelModel):
    id: str
    organization_id: str
    invoice_number: str
    customer_id: str | None = None
    customer_name: str = ""
    booking_id: str | None = None
    booking_label: str = ""
    plan_id: str | None = None
    plan_name: str = ""
    invoice_raised_date: date
    security_amount_deposited: Decimal
    invoice_amount: Decimal
    is_gst_invoice: bool
    gst_amount: Decimal
    paid: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    status: Literal["pending", "partially_paid", "paid"]
    created_at: datetime

    @field_serializer("security_amount_deposited", "invoice_amount", "gst_amount", "paid", "outstanding")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class ReceiptCreate(CamelModel):
    invoice_id: UUID
    receipt_date: date
    receipt_amount: Decimal
    payment_mode: Literal["Cash", "Card", "UPI"]
    transaction_last4: str | None = Field(default=None, max_length=4)

    @field_validator("receipt_amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        return _money(value)


class ReceiptOut(CamelModel):
    id: str
    organization_id: str
    invoice_id: str
    invoice_number: str = ""
    receipt_date: date
    receipt_amount: Decimal
    pending_amount: Decimal
    payment_mode: str
    transaction_last4: str | None = None
    entered_by: str = ""
    created_at: datetime

    @field_serializer("receipt_amount", "pending_amount")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
