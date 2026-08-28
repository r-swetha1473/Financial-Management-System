"""Catalog request/response schemas. Updates are out of scope — create/list/get only."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from app.schemas.common import CamelModel


def _blank(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ProductCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    vin_number: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    battery_type: str | None = Field(default=None, max_length=100)
    body_color: str | None = Field(default=None, max_length=100)
    status: Literal["active", "inactive"] = "active"

    @field_validator("vin_number", "model", "battery_type", "body_color", mode="before")
    @classmethod
    def blank_optional(cls, value: object) -> object:
        return _blank(value)


class ProductOut(CamelModel):
    id: str
    organization_id: str
    name: str
    vin_number: str | None = None
    model: str | None = None
    battery_type: str | None = None
    body_color: str | None = None
    status: str
    created_at: datetime


class CategoryCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class CategoryOut(CamelModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime


class SubcategoryCreate(CamelModel):
    category_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class SubcategoryOut(CamelModel):
    id: str
    organization_id: str
    category_id: str
    category_name: str = ""
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime


class OfferingCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    product_id: UUID | None = None
    description: str | None = None
    amount: Decimal = Decimal("0")
    is_active: bool = True

    @field_validator("product_id", mode="before")
    @classmethod
    def empty_product(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))


class OfferingOut(CamelModel):
    id: str
    organization_id: str
    product_id: str | None = None
    product_name: str = ""
    name: str
    description: str | None = None
    amount: Decimal
    is_active: bool
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value.quantize(Decimal("0.0001")), "f")
