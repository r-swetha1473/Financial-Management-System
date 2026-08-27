"""Canonical demo tenant IDs — must match frontend seed organizationId."""

from uuid import UUID

# Same value as 001_schema.sql INSERT and frontend DEMO_ORGANIZATION_ID
DEMO_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_ORGANIZATION_NAME = "Demo Business Co."
DEMO_ORGANIZATION_SLUG = "demo-business"

DEMO_ADMIN_ID = UUID("00000000-0000-0000-0000-000000000011")
DEMO_MANAGER_ID = UUID("00000000-0000-0000-0000-000000000012")
DEMO_FINANCE_ID = UUID("00000000-0000-0000-0000-000000000013")
DEMO_OPERATOR_ID = UUID("00000000-0000-0000-0000-000000000014")
DEMO_VIEWER_ID = UUID("00000000-0000-0000-0000-000000000015")

DEMO_USERS = (
    {
        "id": DEMO_ADMIN_ID,
        "username": "admin",
        "email": "admin@demo-business.com",
        "full_name": "System Administrator",
        "role": "ADMIN",
        "password": "admin123",
    },
    {
        "id": DEMO_MANAGER_ID,
        "username": "manager",
        "email": "manager@demo-business.com",
        "full_name": "Operations Manager",
        "role": "MANAGER",
        "password": "manager123",
    },
    {
        "id": DEMO_FINANCE_ID,
        "username": "finance",
        "email": "finance@demo-business.com",
        "full_name": "Finance Lead",
        "role": "FINANCE",
        "password": "finance123",
    },
    {
        "id": DEMO_OPERATOR_ID,
        "username": "operator",
        "email": "operator@demo-business.com",
        "full_name": "Records Operator",
        "role": "OPERATOR",
        "password": "operator123",
    },
    {
        "id": DEMO_VIEWER_ID,
        "username": "viewer",
        "email": "viewer@demo-business.com",
        "full_name": "Read-only Viewer",
        "role": "VIEWER",
        "password": "viewer123",
    },
)
