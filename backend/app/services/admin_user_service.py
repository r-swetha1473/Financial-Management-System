"""Admin user service. Last-admin and self-deactivation checks lock org user rows."""

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.audit import write_audit_log
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.admin_user import UserCreate, UserOut, UserUpdate

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _to_out(user: User) -> UserOut:
    created = user.created_at.isoformat() if user.created_at else ""
    return UserOut(
        id=str(user.id),
        organization_id=str(user.organization_id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=created,
    )


def _assert_username(username: str) -> None:
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username may contain letters, numbers, dots, underscores, and hyphens.",
        )


def _assert_admin_invariants(
    locked_users: list[User],
    *,
    actor_id: UUID,
    target: User | None,
    next_role: str,
    next_active: bool,
) -> None:
    if target is not None and target.id == actor_id and not next_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    remaining_admin = False
    for row in locked_users:
        role = next_role if target is not None and row.id == target.id else row.role
        active = next_active if target is not None and row.id == target.id else row.is_active
        if role == "ADMIN" and active:
            remaining_admin = True
            break
    if target is None and next_role == "ADMIN" and next_active:
        remaining_admin = True
    if not remaining_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The organization must keep at least one active administrator.",
        )


async def list_users(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    search: str = "",
    status_filter: str = "",
    role: str = "",
) -> tuple[list[UserOut], int]:
    rows, total = await UserRepository(session, tenant_id).list_page(
        page, page_size, search=search, status=status_filter, role=role
    )
    return [_to_out(row) for row in rows], total


async def create_user(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    payload: UserCreate,
) -> UserOut:
    _assert_username(payload.username)
    repo = UserRepository(session, tenant_id)
    locked = await repo.lock_all_in_org()
    email = payload.email.strip().lower()
    username = payload.username.strip()
    if any(row.email.lower() == email for row in locked):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in the organization.",
        )
    if any(row.username.lower() == username.lower() for row in locked):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists in the organization.",
        )
    _assert_admin_invariants(
        locked,
        actor_id=actor_id,
        target=None,
        next_role=payload.role,
        next_active=payload.is_active,
    )
    user = User(
        organization_id=tenant_id,
        username=username,
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    session.add(user)
    await session.flush()
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action="create",
        entity_name="user",
        entity_id=user.id,
        old_values=None,
        new_values={"email": email, "username": username, "role": payload.role},
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists in the organization.",
        ) from exc
    await session.refresh(user)
    return _to_out(user)


async def update_user(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    user_id: UUID,
    payload: UserUpdate,
) -> UserOut:
    _assert_username(payload.username)
    repo = UserRepository(session, tenant_id)
    locked = await repo.lock_all_in_org()
    target = next((row for row in locked if row.id == user_id), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization.",
        )
    email = payload.email.strip().lower()
    username = payload.username.strip()
    if any(row.email.lower() == email and row.id != user_id for row in locked):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in the organization.",
        )
    if any(row.username.lower() == username.lower() and row.id != user_id for row in locked):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists in the organization.",
        )
    _assert_admin_invariants(
        locked,
        actor_id=actor_id,
        target=target,
        next_role=payload.role,
        next_active=payload.is_active,
    )
    old_values = {
        "email": target.email,
        "username": target.username,
        "role": target.role,
        "is_active": target.is_active,
    }
    target.username = username
    target.email = email
    target.full_name = payload.full_name.strip()
    target.role = payload.role
    target.is_active = payload.is_active
    if payload.password:
        if len(payload.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters.",
            )
        target.password_hash = hash_password(payload.password)
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action="update",
        entity_name="user",
        entity_id=target.id,
        old_values=old_values,
        new_values={
            "email": email,
            "username": username,
            "role": payload.role,
            "is_active": payload.is_active,
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists in the organization.",
        ) from exc
    await session.refresh(target)
    return _to_out(target)
