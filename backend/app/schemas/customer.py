"""Customer request/response schemas. Table is customer_skg; API field gstin maps to gst_number."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_serializer, field_validator

from app.schemas.common import CamelModel


class CustomerCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    gstin: str | None = Field(default=None, max_length=50)
    state: str | None = Field(default=None, max_length=100)
    credit_limit: Decimal | None = None

    @field_validator("credit_limit", mode="before")
    @classmethod
    def empty_credit_to_none(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return Decimal(str(value))


class CustomerOut(CamelModel):
    id: str
    organization_id: str
    name: str
    address: str | None = None
    gstin: str | None = None
    state: str | None = None
    credit_limit: Decimal | None = None
    created_at: datetime

    @field_serializer("credit_limit")
    def serialize_credit_limit(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.quantize(Decimal("0.0001")), "f")
