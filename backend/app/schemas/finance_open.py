"""Finance accounts, transactions, income, GST summary, reconciliation note."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import field_serializer

from app.schemas.common import CamelModel


class FinanceAccountOut(CamelModel):
    id: str
    organization_id: str
    name: str
    account_type: str
    account_number: str | None = None
    balance: Decimal
    is_active: bool
    created_at: datetime | None = None

    @field_serializer("balance")
    def serialize_balance(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class FinanceTransactionOut(CamelModel):
    id: str
    organization_id: str
    account_id: str
    account_name: str = ""
    transaction_type: str
    amount: Decimal
    reference_type: str | None = None
    reference_id: str | None = None
    description: str | None = None
    transaction_date: date
    reconciled: bool
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class IncomeRecordOut(CamelModel):
    id: str
    source_type: Literal["collection", "receipt"]
    source_id: str
    source_route: str
    customer_name: str = ""
    document_number: str = ""
    amount: Decimal
    gst_amount: Decimal = Decimal("0")
    date: date
    status: str = ""

    @field_serializer("amount", "gst_amount")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class GstSummaryOut(CamelModel):
    input_gst: Decimal
    output_gst: Decimal
    net: Decimal
    expenses: Decimal = Decimal("0")
    supplier: Decimal
    output_legacy: Decimal
    output_o2c: Decimal
    date_from: date | None = None
    date_to: date | None = None

    @field_serializer("input_gst", "output_gst", "net", "expenses", "supplier", "output_legacy", "output_o2c")
    def serialize_money(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")


class ReconciliationNoteIn(CamelModel):
    note: str = ""


class ReconciliationNoteOut(CamelModel):
    organization_id: str
    note: str
    updated_at: datetime | None = None
