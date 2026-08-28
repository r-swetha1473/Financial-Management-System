"""Catalog endpoints: products, categories, subcategories, offerings. Create/list/get only."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.paging import paginated
from app.core.deps import CurrentUser, require_permission
from app.db.session import get_db
from app.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    OfferingCreate,
    OfferingOut,
    ProductCreate,
    ProductOut,
    SubcategoryCreate,
    SubcategoryOut,
)
from app.schemas.common import ApiResponse, PaginatedResponse
from app.services import catalog_service

products_router = APIRouter(prefix="/products", tags=["Products"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])
subcategories_router = APIRouter(prefix="/subcategories", tags=["Subcategories"])
offerings_router = APIRouter(prefix="/offerings", tags=["Offerings"])


@products_router.get("", response_model=PaginatedResponse[ProductOut])
async def list_products(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str = "",
    status: str = "",
):
    items, total = await catalog_service.list_products(session, current.tenant_id, page, page_size, search, status)
    return paginated(items, total, page, page_size)


@products_router.get("/{product_id}", response_model=ApiResponse[ProductOut])
async def get_product(
    product_id: UUID,
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await catalog_service.get_product(session, current.tenant_id, product_id))


@products_router.post("", response_model=ApiResponse[ProductOut], status_code=201)
async def create_product(
    payload: ProductCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await catalog_service.create_product(session, current.tenant_id, payload))


@categories_router.get("", response_model=PaginatedResponse[CategoryOut])
async def list_categories(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await catalog_service.list_categories(session, current.tenant_id, page, page_size)
    return paginated(items, total, page, page_size)


@categories_router.post("", response_model=ApiResponse[CategoryOut], status_code=201)
async def create_category(
    payload: CategoryCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await catalog_service.create_category(session, current.tenant_id, payload))


@subcategories_router.get("", response_model=PaginatedResponse[SubcategoryOut])
async def list_subcategories(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category_id: UUID | None = None,
):
    items, total = await catalog_service.list_subcategories(session, current.tenant_id, page, page_size, category_id)
    return paginated(items, total, page, page_size)


@subcategories_router.post("", response_model=ApiResponse[SubcategoryOut], status_code=201)
async def create_subcategory(
    payload: SubcategoryCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await catalog_service.create_subcategory(session, current.tenant_id, payload))


@offerings_router.get("", response_model=PaginatedResponse[OfferingOut])
async def list_offerings(
    current: Annotated[CurrentUser, Depends(require_permission("view"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = await catalog_service.list_offerings(session, current.tenant_id, page, page_size)
    return paginated(items, total, page, page_size)


@offerings_router.post("", response_model=ApiResponse[OfferingOut], status_code=201)
async def create_offering(
    payload: OfferingCreate,
    current: Annotated[CurrentUser, Depends(require_permission("create"))],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    return ApiResponse(data=await catalog_service.create_offering(session, current.tenant_id, payload))
