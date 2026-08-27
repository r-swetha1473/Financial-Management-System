"""Delivery schemas. delivery_number and organization_id are server-assigned."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import CamelModel

DeliveryStatus = Literal["delivered", "cancelled"]


class DeliveryCreate(CamelModel):
    sales_order_id: UUID
    delivery_date: date | None = None
    status: DeliveryStatus = "delivered"

    @field_validator("sales_order_id", mode="before")
    @classmethod
    def empty_sales_order_rejected(cls, value: object) -> object:
        if value == "":
            return None
        return value


class DeliveryOut(CamelModel):
    id: str
    organization_id: str
    sales_order_id: str
    order_number: str = ""
    customer_id: str | None = None
    customer_name: str = ""
    delivery_number: str
    status: str
    delivery_date: date
    created_at: datetime
