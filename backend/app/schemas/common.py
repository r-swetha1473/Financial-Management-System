"""Shared Pydantic schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ApiResponse(CamelModel, Generic[T]):
    success: bool = True
    data: T
    message: str | None = None


class ApiError(CamelModel):
    code: str
    message: str
    details: dict[str, list[str]] | None = None
    detail: str | None = None


class PaginationMeta(CamelModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class PaginatedResponse(CamelModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: PaginationMeta
