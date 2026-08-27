"""Authentication schemas."""

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserSession(CamelModel):
    user_id: str
    email: EmailStr
    full_name: str
    role: str
    organization_id: str
    organization_name: str


class LoginResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session: UserSession


class RefreshRequest(CamelModel):
    refresh_token: str
