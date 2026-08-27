"""Audit log list API: tenant isolation, view RBAC, filters, append-only table."""

from __future__ import annotations

import asyncio
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.ids import DEMO_ADMIN_ID
from app.core.security import hash_password
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.audit_log import AuditLog
from app.models.finance_account import FinanceAccount
from app.models.finance_transaction import FinanceTransaction
from app.models.organization import Organization
from app.models.user import User, UserSession

AUDIT_URL = "/api/v1/admin/audit-logs"
EXPENSES_URL = "/api/v1/finance/expenses"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "audit-log-test-"
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


class AuditLogApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_expense_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_expense_ids = []
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-audit.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Audit Isolation Org",
                slug=f"iso-aud-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-aud-admin",
                    email=email,
                    full_name="Audit Isolation Admin",
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
            if cls.created_expense_ids:
                await session.execute(
                    delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_expense_ids))
                )
                await session.execute(
                    delete(FinanceTransaction).where(
                        FinanceTransaction.id.in_(cls.created_expense_ids)
                    )
                )
            marked = select(FinanceTransaction.id).where(
                FinanceTransaction.description.like(f"{TEST_MARKER}%")
            )
            await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(marked)))
            await session.execute(
                delete(FinanceTransaction).where(
                    FinanceTransaction.description.like(f"{TEST_MARKER}%")
                )
            )
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
                await session.execute(
                    delete(FinanceTransaction).where(
                        FinanceTransaction.organization_id == cls.org_b_id
                    )
                )
                await session.execute(
                    delete(FinanceAccount).where(FinanceAccount.organization_id == cls.org_b_id)
                )
                org_users = select(User.id).where(User.organization_id == cls.org_b_id)
                await session.execute(delete(UserSession).where(UserSession.user_id.in_(org_users)))
                await session.execute(delete(User).where(User.organization_id == cls.org_b_id))
                await session.execute(delete(Organization).where(Organization.id == cls.org_b_id))

        await _with_own_session(work)

    def _login(self, email: str, password: str) -> str:
        response = self.client.post(LOGIN_URL, json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        token = _access_token(response.json())
        self.assertTrue(token)
        return token

    def _auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _create_expense(self, token: str) -> dict:
        description = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token),
            json={
                "cost": "12.0000",
                "expenseDate": "2026-08-27",
                "productServiceName": description,
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        data = create.json()["data"]
        self.created_expense_ids.append(data["id"])
        return data

    def test_admin_lists_audit_with_actor_and_diff(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        created = self._create_expense(token)
        listed = self.client.get(
            f"{AUDIT_URL}?page=1&page_size=100&entity_name=finance_expense&action=create",
            headers=self._auth(token),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        self.assertTrue(body.get("success"))
        match = next((row for row in body["data"] if row["entityId"] == created["id"]), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["action"], "create")
        self.assertEqual(match["entityName"], "finance_expense")
        self.assertEqual(match["userEmail"], "admin@demo-business.com")
        self.assertEqual(match["userName"], "System Administrator")
        self.assertEqual(match["userId"], str(DEMO_ADMIN_ID))
        self.assertIsNone(match.get("oldValues"))
        self.assertIsInstance(match["newValues"], dict)
        self.assertIn("amount", match["newValues"])
        self.assertNotIn("ipAddress", match)
        meta = body["meta"]
        self.assertEqual(meta.get("page"), 1)
        self.assertGreaterEqual(meta.get("total") or 0, 1)

        aliased = self.client.get(
            f"{AUDIT_URL}?entity_type=finance_expense&page=1&page_size=100",
            headers=self._auth(token),
        )
        self.assertEqual(aliased.status_code, 200, aliased.text)
        self.assertIn(created["id"], [row["entityId"] for row in aliased.json()["data"]])

        by_actor = self.client.get(
            f"{AUDIT_URL}?actor_user_id={DEMO_ADMIN_ID}&entity_name=finance_expense&page=1&page_size=100",
            headers=self._auth(token),
        )
        self.assertEqual(by_actor.status_code, 200, by_actor.text)
        self.assertTrue(all(row["userId"] == str(DEMO_ADMIN_ID) for row in by_actor.json()["data"]))

    def test_viewer_can_list_audit_logs(self) -> None:
        token = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.get(f"{AUDIT_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json().get("success"))

    def test_org_b_admin_cannot_see_org_a_audit_trail(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        created = self._create_expense(token_a)
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{AUDIT_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["entityId"] for item in listed_b.json()["data"]]
        self.assertNotIn(created["id"], ids_b)
        org_ids = {item["organizationId"] for item in listed_b.json()["data"]}
        self.assertNotIn("00000000-0000-0000-0000-000000000001", org_ids)

    def test_audit_logs_are_append_only(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        created = self._create_expense(token)
        expense_id = created["id"]

        async def try_mutate():
            async def work(session: AsyncSession):
                row = await session.scalar(select(AuditLog).where(AuditLog.entity_id == expense_id))
                self.assertIsNotNone(row)
                with self.assertRaises(Exception):
                    await session.execute(
                        update(AuditLog).where(AuditLog.id == row.id).values(action="tamper")
                    )
                    await session.flush()
                await session.rollback()
                with self.assertRaises(Exception):
                    await session.execute(delete(AuditLog).where(AuditLog.id == row.id))
                    await session.flush()
                await session.rollback()
                blocked = await session.scalar(
                    select(AuditLog.action).where(AuditLog.entity_id == expense_id)
                )
                self.assertEqual(blocked, "create")

            return await _with_own_session(work)

        _run(try_mutate())

        post = self.client.post(AUDIT_URL, headers=self._auth(token), json={})
        self.assertIn(post.status_code, (404, 405, 422))


if __name__ == "__main__":
    unittest.main()
