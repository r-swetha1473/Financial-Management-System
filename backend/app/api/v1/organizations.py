"""Organization API routes. Tenant is always the JWT organization except POST (provisioning)."""

from typing import Annotated
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user, require_permission
from app.core.security import hash_password
from app.db.audit import write_audit_log
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.organization import OrganizationCreate, OrganizationSummary, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["Organizations"])

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _summary(organization: Organization) -> OrganizationSummary:
    return OrganizationSummary(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        is_active=organization.is_active,
    )


@router.get("/current", response_model=ApiResponse[OrganizationSummary])
async def get_current_organization(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[OrganizationSummary]:
    organization = await session.get(Organization, current.tenant_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return ApiResponse(data=_summary(organization))


@router.post("", response_model=ApiResponse[OrganizationSummary], status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    current: Annotated[CurrentUser, Depends(require_permission("admin"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[OrganizationSummary]:
    name = payload.name.strip()
    slug = payload.slug.strip().lower()
    username = payload.admin_username.strip()
    email = str(payload.admin_email).strip().lower()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization name is required.")
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug must be lowercase letters, numbers, and hyphens.",
        )
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username may contain letters, numbers, dots, underscores, and hyphens.",
        )
    taken = await session.execute(select(Organization).where(Organization.slug == slug))
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This organization slug is already in use.")

    organization = Organization(name=name, slug=slug, is_active=payload.is_active)
    session.add(organization)
    await session.flush()
    session.add(
        User(
            organization_id=organization.id,
            username=username,
            email=email,
            full_name=payload.admin_full_name.strip(),
            password_hash=hash_password(payload.admin_password),
            role="ADMIN",
            is_active=True,
        )
    )
    write_audit_log(
        session,
        organization_id=current.tenant_id,
        user_id=current.user_id,
        action="create",
        entity_name="organization",
        entity_id=organization.id,
        old_values=None,
        new_values={"name": name, "slug": slug},
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This organization slug is already in use.",
        ) from exc
    await session.refresh(organization)
    return ApiResponse(data=_summary(organization))


@router.put("/current", response_model=ApiResponse[OrganizationSummary])
async def update_current_organization(
    payload: OrganizationUpdate,
    current: Annotated[CurrentUser, Depends(require_permission("admin"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[OrganizationSummary]:
    organization = await session.get(Organization, current.tenant_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    name = payload.name.strip()
    slug = payload.slug.strip().lower()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization name is required.")
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug must be lowercase letters, numbers, and hyphens.",
        )
    taken = await session.execute(
        select(Organization).where(Organization.slug == slug, Organization.id != organization.id)
    )
    if taken.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This organization slug is already in use.")
    organization.name = name
    organization.slug = slug
    organization.is_active = payload.is_active
    await session.commit()
    await session.refresh(organization)
    return ApiResponse(data=_summary(organization))
