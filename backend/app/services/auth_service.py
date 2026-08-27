"""Authentication against PostgreSQL users. Tenant is taken from the user row."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User
from app.models.user import UserSession as DbUserSession
from app.schemas.auth import LoginResponse, UserSession


def _session_payload(user: User, organization: Organization) -> UserSession:
    return UserSession(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=str(user.organization_id),
        organization_name=organization.name,
    )


def _tokens(user: User, organization: Organization) -> tuple[str, str]:
    claims = {
        "organization_id": str(organization.id),
        "role": user.role,
        "email": user.email,
    }
    access = create_access_token(str(user.id), claims)
    refresh = create_refresh_token(str(user.id), {"organization_id": str(organization.id)})
    return access, refresh


async def authenticate(session: AsyncSession, email: str, password: str) -> tuple[User, Organization]:
    result = await session.execute(select(User).where(func.lower(User.email) == email.strip().lower()))
    users = list(result.scalars().all())
    matched: User | None = None
    for candidate in users:
        if verify_password(password, candidate.password_hash):
            matched = candidate
            break
    if matched is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not matched.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is inactive. Contact an administrator.",
        )
    organization = await session.get(Organization, matched.organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This organization is inactive.")
    return matched, organization


async def issue_login(session: AsyncSession, user: User, organization: Organization) -> LoginResponse:
    access, refresh = _tokens(user, organization)
    session.add(
        DbUserSession(
            user_id=user.id,
            organization_id=organization.id,
            refresh_token=hash_refresh_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await session.commit()
    return LoginResponse(access_token=access, refresh_token=refresh, session=_session_payload(user, organization))


async def refresh_login(session: AsyncSession, refresh_token: str) -> LoginResponse:
    payload = decode_token(refresh_token)
    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    token_hash = hash_refresh_token(refresh_token)
    result = await session.execute(
        select(DbUserSession).where(
            DbUserSession.refresh_token == token_hash,
            DbUserSession.expires_at > datetime.now(UTC),
        )
    )
    stored = result.scalar_one_or_none()
    if stored is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = await session.get(User, stored.user_id)
    organization = await session.get(Organization, stored.organization_id)
    if user is None or not user.is_active or organization is None or not organization.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    access, new_refresh = _tokens(user, organization)
    stored.refresh_token = hash_refresh_token(new_refresh)
    stored.expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    await session.commit()
    return LoginResponse(access_token=access, refresh_token=new_refresh, session=_session_payload(user, organization))


async def revoke_sessions(session: AsyncSession, user_id: UUID) -> None:
    result = await session.execute(select(DbUserSession).where(DbUserSession.user_id == user_id))
    for row in result.scalars().all():
        await session.delete(row)
    await session.commit()
