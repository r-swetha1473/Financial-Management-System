"""Payable schemas. outstanding is a stored cache; live compute remains source of truth."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import field_serializer

from app.schemas.common import CamelModel


class PayableOut(CamelModel):
    id: str
    organization_id: str
    source_type: str
    source_id: str
    invoice_number: str = ""
    vendor_id: str
    vendor_name: str = ""
    amount: Decimal
    outstanding: Decimal
    due_date: date | None = None
    status: str
    created_at: datetime

    @field_serializer("amount", "outstanding")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
