"""Expense schemas. Posted as finance_transactions debit; organization_id is server-assigned.

finance_transactions has no category/GST/status columns. Angular's extra form fields
are accepted on create (extra ignore) and returned as empty defaults on read.
Optional vendorId is stored on reference_id with no FK to vendors.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import field_serializer, field_validator

from app.schemas.common import CamelModel


def _parse_money(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class ExpenseCreate(CamelModel):
    cost: Decimal
    expense_date: date
    product_service_name: str | None = None
    vendor_id: UUID | None = None

    @field_validator("vendor_id", mode="before")
    @classmethod
    def empty_vendor_is_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("cost", mode="before")
    @classmethod
    def parse_cost(cls, value: object) -> Decimal:
        return _parse_money(value)


class ExpenseOut(CamelModel):
    id: str
    organization_id: str
    vendor_id: str | None = None
    vendor_name: str = ""
    category_id: str | None = None
    category_name: str = ""
    subcategory_id: str | None = None
    subcategory_name: str = ""
    product_id: str | None = None
    product_name: str = ""
    product_service_name: str = ""
    sku: str = ""
    quantity: Decimal = Decimal("1.0000")
    unit_price: Decimal = Decimal("0.0000")
    cost: Decimal
    gst_percentage: Decimal = Decimal("0.00")
    gst_amount: Decimal = Decimal("0.0000")
    purchase_order_number: str = ""
    expense_date: date
    entered_by: str = ""
    status: Literal["pending", "approved", "rejected"] = "approved"
    created_at: datetime

    @field_serializer("cost", "quantity", "unit_price", "gst_amount")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")

    @field_serializer("gst_percentage")
    def serialize_gst_pct(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.01")), "f")
