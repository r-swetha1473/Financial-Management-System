"""Vendor request/response schemas. organization_id is never accepted from the client."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

VendorStatus = Literal["active", "inactive"]


class VendorCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    poc_name: str | None = Field(default=None, max_length=255)
    poc_email: str | None = Field(default=None, max_length=255)
    gstin: str | None = Field(default=None, max_length=50)
    state: str | None = Field(default=None, max_length=100)
    status: VendorStatus = "active"


class VendorOut(CamelModel):
    id: str
    organization_id: str
    name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    poc_name: str | None = None
    poc_email: str | None = None
    gstin: str | None = None
    state: str | None = None
    status: str
    created_at: datetime
