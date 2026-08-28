"""Quotation schemas. quote_number and organization_id are server-assigned.

User-facing name is Subscribed Plan. JSON field names (quoteNumber, etc.) stay
for contract compatibility. plan_duration is days.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from app.schemas.common import CamelModel

QuotationStatus = Literal["draft", "sent", "accepted", "rejected", "converted"]
BillingCycle = Literal["one_time", "weekly", "monthly"]


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    text = str(value).strip().replace(",", "")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Amount must be a non-negative number.") from exc
    if amount < 0:
        raise ValueError("Amount must be a non-negative number.")
    return amount


class QuotationCreate(CamelModel):
    customer_id: UUID
    quote_date: date | None = None
    valid_until: date | None = None
    total_amount: Decimal = Decimal("0")
    status: QuotationStatus = "draft"
    plan_duration: int | None = Field(default=None, ge=1)
    billing_cycle: BillingCycle | None = None
    deposit_amount: Decimal = Decimal("0")

    @field_validator("customer_id", mode="before")
    @classmethod
    def empty_customer_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("valid_until", "billing_cycle", mode="before")
    @classmethod
    def empty_optional_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("plan_duration", mode="before")
    @classmethod
    def empty_duration_to_none(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return value

    @field_validator("total_amount", "deposit_amount", mode="before")
    @classmethod
    def parse_money_fields(cls, value: object) -> Decimal:
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
    plan_duration: int | None = None
    billing_cycle: str | None = None
    deposit_amount: Decimal = Decimal("0")
    created_at: datetime

    @field_serializer("total_amount", "deposit_amount")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
