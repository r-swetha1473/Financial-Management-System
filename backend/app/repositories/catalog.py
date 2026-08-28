"""Catalog persistence. Tenant is injected at construction."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.catalog import Category, Offering, Product, Subcategory


class CatalogRepository(TenantScopedRepository):
    def _tenant(self, model):
        return for_tenant(model.organization_id, self.tenant_id)

    async def list_products(self, page: int, page_size: int, search: str = "", status: str = "") -> tuple[list[Product], int]:
        tenant = self._tenant(Product)
        filters = [tenant]
        if search.strip():
            like = f"%{search.strip()}%"
            filters.append(Product.name.ilike(like) | Product.model.ilike(like) | Product.vin_number.ilike(like))
        if status.strip():
            filters.append(Product.status == status.strip())
        total = await self.session.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
        stmt = select(Product).where(*filters).order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.scalars(stmt)).all()), int(total)

    async def get_product(self, product_id: UUID) -> Product | None:
        return await self.session.scalar(select(Product).where(Product.id == product_id, self._tenant(Product)))

    async def create_product(self, **kwargs) -> Product:
        row = Product(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def list_categories(self, page: int, page_size: int) -> tuple[list[Category], int]:
        tenant = self._tenant(Category)
        total = await self.session.scalar(select(func.count()).select_from(Category).where(tenant)) or 0
        stmt = select(Category).where(tenant).order_by(Category.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.scalars(stmt)).all()), int(total)

    async def get_category(self, category_id: UUID) -> Category | None:
        return await self.session.scalar(select(Category).where(Category.id == category_id, self._tenant(Category)))

    async def create_category(self, **kwargs) -> Category:
        row = Category(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def list_subcategories(
        self, page: int, page_size: int, category_id: UUID | None
    ) -> tuple[list[tuple[Subcategory, str]], int]:
        tenant = self._tenant(Subcategory)
        filters = [tenant]
        if category_id is not None:
            filters.append(Subcategory.category_id == category_id)
        total = await self.session.scalar(select(func.count()).select_from(Subcategory).where(*filters)) or 0
        stmt = (
            select(Subcategory, Category.name)
            .join(Category, Category.id == Subcategory.category_id)
            .where(*filters)
            .order_by(Subcategory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1] or "") for row in rows], int(total)

    async def create_subcategory(self, **kwargs) -> Subcategory:
        row = Subcategory(organization_id=self.tenant_id, **kwargs)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def list_offerings(self, page: int, page_size: int) -> tuple[list[tuple[Offering, str]], int]:
        tenant = self._tenant(Offering)
        total = await self.session.scalar(select(func.count()).select_from(Offering).where(tenant)) or 0
        stmt = (
            select(Offering, Product.name)
            .outerjoin(Product, Product.id == Offering.product_id)
            .where(tenant)
            .order_by(Offering.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).all())
        return [(row[0], row[1] or "") for row in rows], int(total)

    async def get_offering(self, offering_id: UUID) -> Offering | None:
        return await self.session.scalar(select(Offering).where(Offering.id == offering_id, self._tenant(Offering)))

    async def create_offering(
        self,
        *,
        name: str,
        product_id: UUID | None,
        description: str | None,
        amount: Decimal,
        is_active: bool,
    ) -> Offering:
        row = Offering(
            organization_id=self.tenant_id,
            name=name,
            product_id=product_id,
            description=description,
            amount=amount,
            is_active=is_active,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
