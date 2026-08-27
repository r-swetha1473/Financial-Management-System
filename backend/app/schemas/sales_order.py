"""Sales-order schemas. order_number and organization_id are server-assigned."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel

SalesOrderStatus = Literal["confirmed", "fulfilled", "cancelled"]


class SalesOrderCreate(CamelModel):
    customer_id: UUID | None = None
    quotation_id: UUID | None = None
    order_date: date | None = None
    total_amount: Decimal = Decimal("0")
    status: SalesOrderStatus = "confirmed"

    @field_validator("customer_id", "quotation_id", mode="before")
    @classmethod
    def empty_uuid_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("total_amount", mode="before")
    @classmethod
    def parse_total_amount(cls, value: object) -> Decimal:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))


class SalesOrderOut(CamelModel):
    id: str
    organization_id: str
    customer_id: str
    customer_name: str = ""
    quotation_id: str | None = None
    quote_number: str = ""
    order_number: str
    status: str
    order_date: date
    total_amount: Decimal
    created_at: datetime

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
