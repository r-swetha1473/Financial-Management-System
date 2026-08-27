"""Admin-provisioned organization onboarding."""

from __future__ import annotations

import asyncio
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User, UserSession

ORGS_URL = "/api/v1/organizations"
LOGIN_URL = "/api/v1/auth/login"


def _run(coro):
    return asyncio.run(coro)


async def _with_own_session(work):
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            result = await work(session)
            await session.commit()
            return result
    finally:
        await engine.dispose()


def _access_token(body: dict) -> str:
    data = body.get("data") or {}
    return data.get("accessToken") or data.get("access_token")


class OrganizationCreateApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    created_org_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_org_ids = []
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @classmethod
    async def _cleanup(cls) -> None:
        async def work(session: AsyncSession):
            await allow_audit_delete_for_tests(session)
            if not cls.created_org_ids:
                return
            await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_org_ids)))
            org_users = select(User.id).where(User.organization_id.in_(cls.created_org_ids))
            await session.execute(delete(UserSession).where(UserSession.user_id.in_(org_users)))
            await session.execute(delete(User).where(User.organization_id.in_(cls.created_org_ids)))
            await session.execute(delete(Organization).where(Organization.id.in_(cls.created_org_ids)))

        await _with_own_session(work)

    def _login(self, email: str, password: str) -> str:
        response = self.client.post(LOGIN_URL, json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return _access_token(response.json())

    def test_admin_provisions_org_with_first_admin(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        slug = f"onboard-{uuid4().hex[:10]}"
        email = f"owner-{uuid4().hex[:8]}@iso-org.example.com"
        created = self.client.post(
            ORGS_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Onboarded Co",
                "slug": slug,
                "isActive": True,
                "adminUsername": "owner",
                "adminEmail": email,
                "adminFullName": "Owner Admin",
                "adminPassword": "owner123",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        org = created.json()["data"]
        self.created_org_ids.append(org["id"])
        self.assertEqual(org["slug"], slug)
        self.assertTrue(org["isActive"])

        login = self.client.post(LOGIN_URL, json={"email": email, "password": "owner123"})
        self.assertEqual(login.status_code, 200, login.text)
        session = login.json()["data"]["session"]
        org_id = session.get("organizationId") or session.get("organization_id")
        self.assertEqual(org_id, org["id"])
        self.assertEqual(session["role"], "ADMIN")

        conflict = self.client.post(
            ORGS_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Dup",
                "slug": slug,
                "adminUsername": "other",
                "adminEmail": f"other-{uuid4().hex[:8]}@iso-org.example.com",
                "adminFullName": "Other",
                "adminPassword": "other123",
            },
        )
        self.assertEqual(conflict.status_code, 409, conflict.text)

    def test_manager_cannot_provision_organization(self) -> None:
        token = self._login("manager@demo-business.com", "manager123")
        response = self.client.post(
            ORGS_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Nope",
                "slug": f"nope-{uuid4().hex[:8]}",
                "adminUsername": "nope",
                "adminEmail": f"nope-{uuid4().hex[:8]}@iso-org.example.com",
                "adminFullName": "Nope",
                "adminPassword": "nope123",
            },
        )
        self.assertEqual(response.status_code, 403, response.text)
