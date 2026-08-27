"""Goods receipt schemas. grn_number and organization_id are server-assigned."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import CamelModel

GoodsReceiptStatus = Literal["received", "cancelled"]


class GoodsReceiptCreate(CamelModel):
    purchase_order_id: UUID
    receipt_date: date | None = None
    status: GoodsReceiptStatus = "received"

    @field_validator("purchase_order_id", mode="before")
    @classmethod
    def empty_po_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value


class GoodsReceiptOut(CamelModel):
    id: str
    organization_id: str
    purchase_order_id: str
    po_number: str = ""
    vendor_id: str | None = None
    vendor_name: str = ""
    grn_number: str
    status: str
    receipt_date: date
    created_at: datetime
