"""Purchase order schemas. po_number and organization_id are server-assigned."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel

PurchaseOrderStatus = Literal["draft", "issued", "received", "closed", "cancelled"]


class PurchaseOrderCreate(CamelModel):
    purchase_request_id: UUID | None = None
    vendor_id: UUID | None = None
    order_date: date | None = None
    total_amount: Decimal = Decimal("0")
    status: PurchaseOrderStatus = "draft"

    @field_validator("vendor_id", "purchase_request_id", mode="before")
    @classmethod
    def empty_uuid_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("total_amount", mode="before")
    @classmethod
    def parse_total_amount(cls, value: object) -> object:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))


class PurchaseOrderOut(CamelModel):
    id: str
    organization_id: str
    purchase_request_id: str | None = None
    purchase_request_number: str = ""
    vendor_id: str
    vendor_name: str = ""
    po_number: str
    status: str
    order_date: date
    total_amount: Decimal
    created_at: datetime

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
