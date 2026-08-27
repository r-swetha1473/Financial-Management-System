"""Cash-basis dashboard aggregates are live and org-scoped; seed cash accounts are unreachable."""

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
from app.main import app
from app.models.organization import Organization
from app.models.user import User, UserSession

CASH_URL = "/api/v1/dashboard/cash-position"
SUMMARY_URL = "/api/v1/dashboard/summary"
LOGIN_URL = "/api/v1/auth/login"
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


class CashPositionApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str

    @classmethod
    def setUpClass(cls) -> None:
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
                name="Cash Isolation Org",
                slug=f"iso-cash-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-cash-admin",
                    email=email,
                    full_name="Cash Isolation Admin",
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
            if cls.org_b_id is None:
                return
            org_users = select(User.id).where(User.organization_id == cls.org_b_id)
            await session.execute(delete(UserSession).where(UserSession.user_id.in_(org_users)))
            await session.execute(delete(User).where(User.organization_id == cls.org_b_id))
            await session.execute(delete(Organization).where(Organization.id == cls.org_b_id))

        await _with_own_session(work)

    def _login(self, email: str, password: str) -> str:
        response = self.client.post(LOGIN_URL, json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return _access_token(response.json())

    def test_empty_org_returns_zeros_not_seed_accounts(self) -> None:
        token = self._login(self.org_b_email, ORG_B_PASSWORD)
        response = self.client.get(CASH_URL, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["data"]
        names = [item["accountName"] for item in items]
        self.assertNotIn("Main Operating Account", names)
        self.assertNotIn("Petty Cash", names)
        self.assertIn("Net cash-basis position", names)
        for item in items:
            self.assertEqual(Decimal(str(item["balance"])), Decimal("0"))

        summary = self.client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(summary.status_code, 200, summary.text)
        data = summary.json()["data"]
        self.assertEqual(Decimal(str(data["cashInHand"])), Decimal("0"))
        self.assertEqual(Decimal(str(data["totalIncome"])), Decimal("0"))
        self.assertEqual(Decimal(str(data["totalExpenses"])), Decimal("0"))
        self.assertNotEqual(data["cashInHand"], "487200.00")

    def test_demo_org_cash_position_is_org_scoped(self) -> None:
        demo = self._login("admin@demo-business.com", "admin123")
        other = self._login(self.org_b_email, ORG_B_PASSWORD)
        demo_items = self.client.get(CASH_URL, headers={"Authorization": f"Bearer {demo}"}).json()["data"]
        other_items = self.client.get(CASH_URL, headers={"Authorization": f"Bearer {other}"}).json()["data"]
        self.assertTrue(demo_items)
        self.assertTrue(other_items)
        self.assertNotIn("Main Operating Account", [item["accountName"] for item in demo_items])

        demo_summary = self.client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {demo}"}).json()["data"]
        other_summary = self.client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {other}"}).json()["data"]
        seed_income = Decimal("2847500.00")
        seed_cash = Decimal("487200.00")
        self.assertNotEqual(Decimal(str(demo_summary["totalIncome"])), seed_income)
        self.assertNotEqual(Decimal(str(demo_summary["cashInHand"])), seed_cash)
        self.assertEqual(Decimal(str(other_summary["totalIncome"])), Decimal("0"))
        self.assertEqual(Decimal(str(other_summary["totalExpenses"])), Decimal("0"))

        by_name = {item["accountName"]: Decimal(str(item["balance"])) for item in demo_items}
        expected_income = by_name["Customer collections"] + by_name["Legacy receipts"]
        expected_outflow = by_name["Expenses (finance transactions)"] + by_name["Supplier payments"]
        expected_net = expected_income - expected_outflow
        self.assertEqual(Decimal(str(demo_summary["totalIncome"])), expected_income)
        self.assertEqual(Decimal(str(demo_summary["totalExpenses"])), expected_outflow)
        self.assertEqual(Decimal(str(demo_summary["cashInHand"])), expected_net)
        if expected_outflow > expected_income:
            self.assertLess(Decimal(str(demo_summary["cashInHand"])), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
