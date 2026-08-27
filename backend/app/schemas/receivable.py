"""Receivable schemas. outstanding is live-computed; stored column is a cache."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import field_serializer

from app.schemas.common import CamelModel


class ReceivableOut(CamelModel):
    id: str
    organization_id: str
    source_type: str
    source_id: str
    invoice_number: str = ""
    customer_id: str
    customer_name: str = ""
    amount: Decimal
    outstanding: Decimal
    due_date: date | None = None
    status: str
    created_at: datetime

    @field_serializer("amount", "outstanding")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
