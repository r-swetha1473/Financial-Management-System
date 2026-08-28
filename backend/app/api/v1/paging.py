"""Shared pagination envelope."""

from math import ceil

from app.schemas.common import PaginatedResponse, PaginationMeta


def paginated(items, total: int, page: int, page_size: int):
    total_pages = ceil(total / page_size) if total else 0
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )
