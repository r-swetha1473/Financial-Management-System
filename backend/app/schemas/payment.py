"""Payment schemas. Payments have no document number; organization_id is server-assigned."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel

PaymentMode = Literal["Cash", "Card", "UPI"]


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class PaymentCreate(CamelModel):
    supplier_invoice_id: UUID
    payment_date: date | None = None
    amount: Decimal
    payment_mode: PaymentMode = "UPI"

    @field_validator("supplier_invoice_id", mode="before")
    @classmethod
    def empty_invoice_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        return _parse_money(value)


class PaymentOut(CamelModel):
    id: str
    organization_id: str
    supplier_invoice_id: str
    invoice_number: str = ""
    vendor_id: str
    vendor_name: str = ""
    payment_date: date
    amount: Decimal
    payment_mode: str
    status: str
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
