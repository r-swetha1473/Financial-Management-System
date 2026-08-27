"""Admin user persistence. Lock org users for last-admin / uniqueness checks."""

from uuid import UUID

from sqlalchemy import func, or_, select

from app.db.repository import TenantScopedRepository
from app.db.tenant import for_tenant
from app.models.user import User


class UserRepository(TenantScopedRepository):
    def _tenant_filter(self):
        return for_tenant(User.organization_id, self.tenant_id)

    async def list_page(
        self,
        page: int,
        page_size: int,
        *,
        search: str = "",
        status: str = "",
        role: str = "",
    ) -> tuple[list[User], int]:
        stmt = select(User).where(self._tenant_filter())
        count_stmt = select(func.count()).select_from(User).where(self._tenant_filter())
        if search:
            pattern = f"%{search.strip()}%"
            filt = or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)
        if status == "active":
            stmt = stmt.where(User.is_active.is_(True))
            count_stmt = count_stmt.where(User.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(User.is_active.is_(False))
            count_stmt = count_stmt.where(User.is_active.is_(False))
        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        total = await self.session.scalar(count_stmt) or 0
        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.scalars(stmt)).all())
        return rows, int(total)

    async def get_for_update(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, self._tenant_filter()).with_for_update()
        return await self.session.scalar(stmt)

    async def lock_all_in_org(self) -> list[User]:
        stmt = select(User).where(self._tenant_filter()).order_by(User.id).with_for_update()
        return list((await self.session.scalars(stmt)).all())

    async def find_by_email(self, email: str) -> User | None:
        stmt = select(User).where(self._tenant_filter(), func.lower(User.email) == email.lower())
        return await self.session.scalar(stmt)

    async def find_by_username(self, username: str) -> User | None:
        stmt = select(User).where(self._tenant_filter(), func.lower(User.username) == username.lower())
        return await self.session.scalar(stmt)
