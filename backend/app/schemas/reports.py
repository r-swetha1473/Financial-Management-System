"""Reference data and report view schemas."""

from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class ReferenceCreate(CamelModel):
    data_type: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    is_active: bool = True


class ReferenceOut(CamelModel):
    id: str
    organization_id: str
    data_type: str
    code: str
    label: str
    is_active: bool
    created_at: datetime


class ReportKpi(CamelModel):
    label: str
    value: str
    tone: str | None = None
    format: str = "money"


class ReportColumn(CamelModel):
    key: str
    label: str
    type: str = "text"


class ReportViewOut(CamelModel):
    key: str
    title: str
    subtitle: str = ""
    note: str = ""
    kpis: list[ReportKpi]
    columns: list[ReportColumn]
    rows: list[dict[str, str]]
