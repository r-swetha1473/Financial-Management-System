"""Admin API routes."""

from fastapi import APIRouter

from app.api.v1.admin import audit_logs, users

router = APIRouter(prefix="/admin")
router.include_router(users.router)
router.include_router(audit_logs.router)
