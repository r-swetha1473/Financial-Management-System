"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, UserSession
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_db)]) -> ApiResponse[LoginResponse]:
    user, organization = await auth_service.authenticate(session, payload.email, payload.password)
    result = await auth_service.issue_login(session, user, organization)
    return ApiResponse(data=result)


@router.post("/logout")
async def logout(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, str]]:
    await auth_service.revoke_sessions(session, current.user_id)
    return ApiResponse(data={"message": "Logged out successfully"})


@router.post("/refresh", response_model=ApiResponse[LoginResponse])
async def refresh_token(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[LoginResponse]:
    result = await auth_service.refresh_login(session, payload.refresh_token)
    return ApiResponse(data=result)


@router.get("/session", response_model=ApiResponse[UserSession])
async def get_session(current: Annotated[CurrentUser, Depends(get_current_user)]) -> ApiResponse[UserSession]:
    return ApiResponse(
        data=UserSession(
            user_id=str(current.user_id),
            email=current.email,
            full_name=current.full_name,
            role=current.role,
            organization_id=str(current.organization_id),
            organization_name=current.organization_name,
        )
    )
