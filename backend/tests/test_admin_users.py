"""Admin users: last-admin and self-deactivation with row locking."""

from __future__ import annotations

import asyncio
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.ids import DEMO_ORGANIZATION_ID
from app.core.security import hash_password
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User, UserSession

USERS_URL = "/api/v1/admin/users"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "adm-usr-"
ORG_B_PASSWORD = "isoadmin123"


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


class AdminUserApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_user_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_user_ids = []
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-org.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Admin Isolation Org",
                slug=f"iso-adm-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-adm-admin",
                    email=email,
                    full_name="Admin Isolation Admin",
                    password_hash=hash_password(ORG_B_PASSWORD),
                    role="ADMIN",
                    is_active=True,
                )
            )
            return org.id

        return await _with_own_session(work)

    @classmethod
    async def _cleanup(cls) -> None:
        async def work(session: AsyncSession):
            await allow_audit_delete_for_tests(session)
            if cls.created_user_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_user_ids)))
                await session.execute(delete(UserSession).where(UserSession.user_id.in_(cls.created_user_ids)))
                await session.execute(delete(User).where(User.id.in_(cls.created_user_ids)))
            await session.execute(delete(User).where(User.username.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
                org_users = select(User.id).where(User.organization_id == cls.org_b_id)
                await session.execute(delete(UserSession).where(UserSession.user_id.in_(org_users)))
                await session.execute(delete(User).where(User.organization_id == cls.org_b_id))
                await session.execute(delete(Organization).where(Organization.id == cls.org_b_id))

        await _with_own_session(work)

    def _login(self, email: str, password: str) -> str:
        response = self.client.post(LOGIN_URL, json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return _access_token(response.json())

    def _auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _create_user(self, token: str, *, role: str = "OPERATOR", extra: dict | None = None) -> dict:
        suffix = uuid4().hex[:8]
        body = {
            "username": f"{TEST_MARKER}{suffix}",
            "email": f"{TEST_MARKER}{suffix}@demo-business.com",
            "fullName": "Test User",
            "role": role,
            "isActive": True,
            "password": "testpass123",
        }
        if extra:
            body.update(extra)
        response = self.client.post(USERS_URL, headers=self._auth(token), json=body)
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_user_ids.append(data["id"])
        return data

    def test_admin_creates_and_lists_users(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        created = self._create_user(admin)
        self.assertEqual(created["role"], "OPERATOR")
        self.assertTrue(created["isActive"])
        self.assertEqual(created["organizationId"], str(DEMO_ORGANIZATION_ID))
        self.assertNotIn("password", created)
        self.assertNotIn("passwordHash", created)

        listed = self.client.get(f"{USERS_URL}?page=1&page_size=100", headers=self._auth(admin))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(created["id"], ids)

    def test_cannot_deactivate_self(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        me = self.client.get(f"{USERS_URL}?page=1&page_size=100", headers=self._auth(admin))
        self.assertEqual(me.status_code, 200, me.text)
        row = next(item for item in me.json()["data"] if item["email"] == "admin@demo-business.com")
        response = self.client.put(
            f"{USERS_URL}/{row['id']}",
            headers=self._auth(admin),
            json={
                "username": row["username"],
                "email": row["email"],
                "fullName": row["fullName"],
                "role": row["role"],
                "isActive": False,
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("cannot deactivate your own", response.text.lower())

    def test_must_keep_at_least_one_active_admin(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        second = self._create_user(admin, role="ADMIN")
        demote = self.client.put(
            f"{USERS_URL}/{second['id']}",
            headers=self._auth(admin),
            json={
                "username": second["username"],
                "email": second["email"],
                "fullName": second["fullName"],
                "role": "OPERATOR",
                "isActive": True,
            },
        )
        self.assertEqual(demote.status_code, 200, demote.text)

        me = self.client.get(f"{USERS_URL}?page=1&page_size=100", headers=self._auth(admin))
        row = next(item for item in me.json()["data"] if item["email"] == "admin@demo-business.com")
        last = self.client.put(
            f"{USERS_URL}/{row['id']}",
            headers=self._auth(admin),
            json={
                "username": row["username"],
                "email": row["email"],
                "fullName": row["fullName"],
                "role": "OPERATOR",
                "isActive": True,
            },
        )
        self.assertEqual(last.status_code, 400, last.text)
        self.assertIn("at least one active administrator", last.text.lower())

    def test_duplicate_email_is_conflict(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        first = self._create_user(admin)
        duplicate = self.client.post(
            USERS_URL,
            headers=self._auth(admin),
            json={
                "username": f"{TEST_MARKER}{uuid4().hex[:8]}",
                "email": first["email"],
                "fullName": "Dup",
                "role": "OPERATOR",
                "isActive": True,
                "password": "testpass123",
            },
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_manager_and_viewer_cannot_manage_users(self) -> None:
        manager = self._login("manager@demo-business.com", "manager123")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        for token in (manager, viewer):
            listed = self.client.get(USERS_URL, headers=self._auth(token))
            self.assertEqual(listed.status_code, 403, listed.text)

    def test_org_b_users_are_invisible_to_org_a(self) -> None:
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        created_b = self._create_user(
            token_b,
            extra={"email": f"{TEST_MARKER}{uuid4().hex[:8]}@iso-org.example.com"},
        )
        self.assertEqual(created_b["organizationId"], str(self.org_b_id))
        admin_a = self._login("admin@demo-business.com", "admin123")
        listed_a = self.client.get(f"{USERS_URL}?page=1&page_size=100", headers=self._auth(admin_a))
        self.assertNotIn(created_b["id"], [item["id"] for item in listed_a.json()["data"]])


if __name__ == "__main__":
    unittest.main()
