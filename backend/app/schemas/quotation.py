"""Quotation schemas. quote_number and organization_id are server-assigned."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel

QuotationStatus = Literal["draft", "sent", "accepted", "rejected", "converted"]


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class QuotationCreate(CamelModel):
    customer_id: UUID
    quote_date: date | None = None
    valid_until: date | None = None
    total_amount: Decimal = Decimal("0")
    status: QuotationStatus = "draft"

    @field_validator("customer_id", mode="before")
    @classmethod
    def empty_customer_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("valid_until", mode="before")
    @classmethod
    def empty_valid_until_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("total_amount", mode="before")
    @classmethod
    def parse_total_amount(cls, value: object) -> Decimal:
        return _parse_money(value)


class QuotationOut(CamelModel):
    id: str
    organization_id: str
    customer_id: str
    customer_name: str = ""
    quote_number: str
    status: str
    quote_date: date
    valid_until: date | None = None
    total_amount: Decimal
    created_at: datetime

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
