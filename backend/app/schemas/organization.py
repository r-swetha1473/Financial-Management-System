"""Organization schemas."""

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class OrganizationSummary(CamelModel):
    id: str
    name: str
    slug: str
    is_active: bool = True


class OrganizationUpdate(CamelModel):
    name: str
    slug: str
    is_active: bool = True


class OrganizationCreate(CamelModel):
    name: str
    slug: str
    is_active: bool = True
    admin_username: str = Field(min_length=1, max_length=100)
    admin_email: EmailStr
    admin_full_name: str = Field(min_length=1, max_length=255)
    admin_password: str = Field(min_length=6)
