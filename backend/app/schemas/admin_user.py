"""Admin user schemas. Password is write-only; never returned."""

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel

USERNAME_PATTERN = r"^[a-zA-Z0-9._-]+$"
ROLES = ("ADMIN", "MANAGER", "FINANCE", "OPERATOR", "VIEWER")


class UserCreate(CamelModel):
    username: str = Field(pattern=USERNAME_PATTERN, min_length=1, max_length=100)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: str
    is_active: bool = True
    password: str = Field(min_length=6)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError("Invalid role.")
        return value

    @field_validator("username", "full_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class UserUpdate(CamelModel):
    username: str = Field(pattern=USERNAME_PATTERN, min_length=1, max_length=100)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: str
    is_active: bool = True
    password: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError("Invalid role.")
        return value

    @field_validator("username", "full_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("password", mode="before")
    @classmethod
    def empty_password_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


class UserOut(CamelModel):
    id: str
    organization_id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
