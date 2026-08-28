"""RBAC map — keep aligned with frontend/src/app/core/rbac/permissions.ts."""

from typing import Literal

Role = Literal["ADMIN", "MANAGER", "FINANCE", "OPERATOR", "VIEWER"]
Permission = Literal["view", "create", "edit", "delete", "approve", "export", "admin", "maintain_reference"]

# maintain_reference matches frontend canMaintainReference (ADMIN | MANAGER).
# Party/lookup master data: vendors, customers, reference-data. Catalog SKUs
# (products/categories/offerings) stay on create so OPERATOR/FINANCE can maintain them.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": {"view", "create", "edit", "delete", "approve", "export", "admin", "maintain_reference"},
    "MANAGER": {"view", "create", "edit", "approve", "export", "maintain_reference"},
    "FINANCE": {"view", "create", "edit", "approve", "export"},
    "OPERATOR": {"view", "create", "edit"},
    "VIEWER": {"view"},
}


def has_permission(role: str | None, permission: str) -> bool:
    if not role:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())
