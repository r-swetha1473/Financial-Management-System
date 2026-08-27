"""Authenticated request context. Organization always comes from the JWT, never the body."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import has_permission
from app.core.security import decode_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    organization_id: UUID
    organization_name: str
    email: str
    full_name: str
    role: str

    @property
    def tenant_id(self) -> UUID:
        """Canonical tenant for every query. Do not read organization_id from request bodies."""
        return self.organization_id


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if payload.get("typ", "access") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    try:
        user_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or not found")

    claimed_org = payload.get("organization_id")
    if claimed_org and str(user.organization_id) != str(claimed_org):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tenant mismatch")

    organization = await session.get(Organization, user.organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This organization is inactive.")

    return CurrentUser(
        user_id=user.id,
        organization_id=user.organization_id,
        organization_name=organization.name,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


def require_permission(permission: str):
    async def _enforce(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if not has_permission(current.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current

    return _enforce
