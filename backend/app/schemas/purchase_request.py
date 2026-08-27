"""Purchase request schemas. request_number and organization_id are server-assigned."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import CamelModel

PurchaseRequestStatus = Literal["draft", "submitted", "approved", "rejected", "converted"]


class PurchaseRequestCreate(CamelModel):
    vendor_id: UUID | None = None
    requested_date: date | None = None
    notes: str | None = None
    status: PurchaseRequestStatus = "draft"

    @field_validator("vendor_id", mode="before")
    @classmethod
    def empty_vendor_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


class PurchaseRequestOut(CamelModel):
    id: str
    organization_id: str
    vendor_id: str | None = None
    vendor_name: str = ""
    request_number: str
    status: str
    requested_by: str | None = None
    requested_by_name: str = ""
    requested_date: date
    notes: str | None = None
    created_at: datetime
