"""Finance expense API: tenant isolation, RBAC, and create+list happy path."""

from __future__ import annotations

import asyncio
import unittest
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.audit_log import AuditLog
from app.models.finance_account import FinanceAccount
from app.models.finance_transaction import FinanceTransaction
from app.models.organization import Organization
from app.models.user import User, UserSession

EXPENSES_URL = "/api/v1/finance/expenses"
SUMMARY_URL = "/api/v1/dashboard/summary"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "finance-expense-test-"
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


class ExpenseApiTests(unittest.TestCase):
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
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-expense.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Expense Isolation Org",
                slug=f"iso-exp-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-exp-admin",
                    email=email,
                    full_name="Isolation Admin",
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

    def test_admin_create_and_list_happy_path(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        before = self.client.get(SUMMARY_URL, headers=self._auth(token))
        self.assertEqual(before.status_code, 200, before.text)
        expenses_before = Decimal(str(before.json()["data"]["totalExpenses"]))
        cash_before = Decimal(str(before.json()["data"]["cashInHand"]))

        description = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token),
            json={
                "cost": "150.5000",
                "expenseDate": "2026-08-27",
                "productServiceName": description,
                "vendorId": "",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()["data"]
        self.created_expense_ids.append(created["id"])
        self.assertEqual(created["productServiceName"], description)
        self.assertEqual(Decimal(str(created["cost"])), Decimal("150.5000"))
        self.assertEqual(created["expenseDate"], "2026-08-27")
        self.assertEqual(created["status"], "approved")
        self.assertEqual(created["gstAmount"], "0.0000")
        self.assertIsNone(created["vendorId"])
        self.assertEqual(created["organizationId"], "00000000-0000-0000-0000-000000000001")

        listed = self.client.get(f"{EXPENSES_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        self.assertTrue(body.get("success"))
        ids = [item["id"] for item in body["data"]]
        self.assertIn(created["id"], ids)
        meta = body["meta"]
        self.assertGreaterEqual(meta.get("total") or 0, 1)
        self.assertEqual(meta.get("page"), 1)
        self.assertEqual(meta.get("pageSize") or meta.get("page_size"), 20)

        fetched = self.client.get(f"{EXPENSES_URL}/{created['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], created["id"])

        after = self.client.get(SUMMARY_URL, headers=self._auth(token))
        self.assertEqual(after.status_code, 200, after.text)
        expenses_after = Decimal(str(after.json()["data"]["totalExpenses"]))
        cash_after = Decimal(str(after.json()["data"]["cashInHand"]))
        self.assertEqual(expenses_after, expenses_before + Decimal("150.5000"))
        self.assertEqual(cash_after, cash_before - Decimal("150.5000"))

    def test_viewer_cannot_create_expense(self) -> None:
        token = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token),
            json={
                "cost": "10.0000",
                "expenseDate": "2026-08-27",
                "productServiceName": f"{TEST_MARKER}blocked",
            },
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_expense_created_in_org_a_is_invisible_to_org_b(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        description = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token_a),
            json={
                "cost": "25.0000",
                "expenseDate": "2026-08-27",
                "productServiceName": description,
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        expense_id = create.json()["data"]["id"]
        self.created_expense_ids.append(expense_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{EXPENSES_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(expense_id, ids_b)

        stolen = self.client.get(f"{EXPENSES_URL}/{expense_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        spoof = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token_b),
            json={
                "cost": "40.0000",
                "expenseDate": "2026-08-27",
                "productServiceName": f"{TEST_MARKER}spoof",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_expense_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))
        self.assertNotEqual(spoofed["organizationId"], "00000000-0000-0000-0000-000000000001")


if __name__ == "__main__":
    unittest.main()
