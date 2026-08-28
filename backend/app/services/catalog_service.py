"""Catalog create/list/get. Updates are out of scope."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category, Offering, Product, Subcategory
from app.repositories.catalog import CatalogRepository
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


def _product_out(row: Product) -> ProductOut:
    return ProductOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        name=row.name,
        vin_number=row.vin_number,
        model=row.model,
        battery_type=row.battery_type,
        body_color=row.body_color,
        status=row.status,
        created_at=row.created_at,
    )


def _category_out(row: Category) -> CategoryOut:
    return CategoryOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        created_at=row.created_at,
    )


async def list_products(session, tenant_id, page, page_size, search: str = "", status: str = ""):
    rows, total = await CatalogRepository(session, tenant_id).list_products(page, page_size, search, status)
    return [_product_out(row) for row in rows], total


async def get_product(session, tenant_id, product_id: UUID) -> ProductOut:
    row = await CatalogRepository(session, tenant_id).get_product(product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in this organization.")
    return _product_out(row)


async def create_product(session, tenant_id, payload: ProductCreate):
    row = await CatalogRepository(session, tenant_id).create_product(
        name=payload.name.strip(),
        vin_number=payload.vin_number,
        model=payload.model,
        battery_type=payload.battery_type,
        body_color=payload.body_color,
        status=payload.status,
    )
    return _product_out(row)


async def list_categories(session, tenant_id, page, page_size):
    rows, total = await CatalogRepository(session, tenant_id).list_categories(page, page_size)
    return [_category_out(row) for row in rows], total


async def create_category(session, tenant_id, payload: CategoryCreate):
    row = await CatalogRepository(session, tenant_id).create_category(
        name=payload.name.strip(),
        description=payload.description,
        is_active=payload.is_active,
    )
    return _category_out(row)


async def list_subcategories(session, tenant_id, page, page_size, category_id: UUID | None):
    rows, total = await CatalogRepository(session, tenant_id).list_subcategories(page, page_size, category_id)
    items = [
        SubcategoryOut(
            id=str(row.id),
            organization_id=str(row.organization_id),
            category_id=str(row.category_id),
            category_name=name,
            name=row.name,
            description=row.description,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row, name in rows
    ]
    return items, total


async def create_subcategory(session: AsyncSession, tenant_id, payload: SubcategoryCreate):
    repo = CatalogRepository(session, tenant_id)
    category = await repo.get_category(payload.category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found in this organization.")
    row = await repo.create_subcategory(
        category_id=payload.category_id,
        name=payload.name.strip(),
        description=payload.description,
        is_active=payload.is_active,
    )
    return SubcategoryOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        category_id=str(row.category_id),
        category_name=category.name,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        created_at=row.created_at,
    )


async def list_offerings(session, tenant_id, page, page_size):
    rows, total = await CatalogRepository(session, tenant_id).list_offerings(page, page_size)
    items = [
        OfferingOut(
            id=str(row.id),
            organization_id=str(row.organization_id),
            product_id=str(row.product_id) if row.product_id else None,
            product_name=name,
            name=row.name,
            description=row.description,
            amount=row.amount,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row, name in rows
    ]
    return items, total


async def create_offering(session, tenant_id, payload: OfferingCreate):
    repo = CatalogRepository(session, tenant_id)
    if payload.product_id is not None:
        product = await repo.get_product(payload.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in this organization.")
        product_name = product.name
    else:
        product_name = ""
    row = await repo.create_offering(
        name=payload.name.strip(),
        product_id=payload.product_id,
        description=payload.description,
        amount=payload.amount,
        is_active=payload.is_active,
    )
    return OfferingOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        product_id=str(row.product_id) if row.product_id else None,
        product_name=product_name,
        name=row.name,
        description=row.description,
        amount=row.amount,
        is_active=row.is_active,
        created_at=row.created_at,
    )
