"""Collection schemas. Collections have no document number; organization_id is server-assigned."""

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


class CollectionCreate(CamelModel):
    sales_invoice_id: UUID
    collection_date: date | None = None
    amount: Decimal
    payment_mode: PaymentMode = "UPI"

    @field_validator("sales_invoice_id", mode="before")
    @classmethod
    def empty_invoice_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        return _parse_money(value)


class CollectionOut(CamelModel):
    id: str
    organization_id: str
    sales_invoice_id: str
    invoice_number: str = ""
    customer_id: str
    customer_name: str = ""
    collection_date: date
    amount: Decimal
    payment_mode: str
    status: str
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
