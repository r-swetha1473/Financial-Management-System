"""Customer request/response schemas. Table is customer_skg; API field gstin maps to gst_number.

GSTIN stays on the contract (nullable) for vendors/GST reporting. The rental customer
create form hides it; it is not deleted.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pydantic import Field, field_serializer, field_validator

from app.schemas.common import CamelModel

_CREDIT_LIMIT = re.compile(r"^\d+(\.\d{1,4})?$")


def _empty_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


class CustomerCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    gstin: str | None = Field(default=None, max_length=50)
    state: str | None = Field(default=None, max_length=100)
    credit_limit: Decimal | None = None
    phone: str | None = Field(default=None, max_length=50)
    drivers_license_number: str | None = Field(default=None, max_length=100)

    @field_validator("address", "gstin", "state", "phone", "drivers_license_number", mode="before")
    @classmethod
    def blank_optional_to_none(cls, value: object) -> object:
        return _empty_to_none(value)

    @field_validator("credit_limit", mode="before")
    @classmethod
    def parse_credit_limit(cls, value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        text = str(value).strip().replace(",", "")
        if not _CREDIT_LIMIT.fullmatch(text):
            raise ValueError("Credit limit must be a non-negative number.")
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError("Credit limit must be a non-negative number.") from exc


def format_file_size(size: int | None) -> str | None:
    if not size:
        return None
    if size < 1024:
        return f"{size} B"
    return f"{(size + 512) // 1024} KB"


class CustomerOut(CamelModel):
    id: str
    organization_id: str
    name: str
    address: str | None = None
    gstin: str | None = None
    state: str | None = None
    credit_limit: Decimal | None = None
    phone: str | None = None
    drivers_license_number: str | None = None
    photo_file_name: str | None = None
    photo_mime_type: str | None = None
    photo_document_id: str | None = None
    address_proof_name: str | None = None
    address_proof_size: str | None = None
    address_proof_type: str | None = None
    address_proof_document_id: str | None = None
    created_at: datetime

    @field_serializer("credit_limit")
    def serialize_credit_limit(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.quantize(Decimal("0.0001")), "f")
