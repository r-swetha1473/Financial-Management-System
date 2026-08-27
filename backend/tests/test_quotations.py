"""O2C quotation API: sequence numbers, customer tenancy, RBAC, and isolation."""

from __future__ import annotations

import asyncio
import unittest
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.user import User, UserSession

QUOTATIONS_URL = "/api/v1/o2c/quotations"
CUSTOMERS_URL = "/api/v1/o2c/customers"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-quote-test-"
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


class QuotationApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_quote_ids: list
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_quote_ids = []
        cls.created_customer_ids = []
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
                name="Quotation Isolation Org",
                slug=f"iso-qt-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-qt-admin",
                    email=email,
                    full_name="Quotation Isolation Admin",
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
            if cls.created_quote_ids:
                await session.execute(delete(Quotation).where(Quotation.id.in_(cls.created_quote_ids)))
            if cls.org_b_id is not None:
                await session.execute(delete(Quotation).where(Quotation.organization_id == cls.org_b_id))
            if cls.created_customer_ids:
                await session.execute(delete(Customer).where(Customer.id.in_(cls.created_customer_ids)))
            await session.execute(delete(Customer).where(Customer.name.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(Customer).where(Customer.organization_id == cls.org_b_id))
                await session.execute(
                    text("DELETE FROM document_sequences WHERE organization_id = :oid"),
                    {"oid": cls.org_b_id},
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

    def _create_customer(self, token: str, name: str | None = None) -> str:
        response = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={"name": name or f"{TEST_MARKER}{uuid4().hex[:8]}"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        customer_id = response.json()["data"]["id"]
        self.created_customer_ids.append(customer_id)
        return customer_id

    def _assert_quote_number(self, value: str, year: int | None = None) -> None:
        year = year or date.today().year
        self.assertRegex(value, rf"^Q-{year}-\d{{3}}$")

    def test_operator_create_and_list_assigns_unique_sequence_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(admin)
        token = self._login("operator@demo-business.com", "operator123")
        year = date.today().year

        first = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={
                "customerId": customer_id,
                "quoteNumber": "Q-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
                "totalAmount": "1500.50",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        a = first.json()["data"]
        self.created_quote_ids.append(a["id"])
        number_a = a.get("quoteNumber") or a.get("quote_number")
        self._assert_quote_number(number_a, year)
        self.assertNotEqual(number_a, "Q-SHOULD-BE-IGNORED")
        self.assertEqual(a["organizationId"], "00000000-0000-0000-0000-000000000001")
        self.assertEqual(a["customerId"], customer_id)
        self.assertEqual(a["status"], "draft")
        self.assertEqual(a.get("totalAmount") or a.get("total_amount"), "1500.5000")

        second = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_id, "status": "sent", "totalAmount": "0"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        b = second.json()["data"]
        self.created_quote_ids.append(b["id"])
        number_b = b.get("quoteNumber") or b.get("quote_number")
        self._assert_quote_number(number_b, year)
        self.assertNotEqual(number_a, number_b)
        self.assertEqual(b["status"], "sent")

        listed = self.client.get(f"{QUOTATIONS_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        ids = [item["id"] for item in body["data"]]
        self.assertIn(a["id"], ids)
        self.assertIn(b["id"], ids)
        meta = body["meta"]
        self.assertGreaterEqual(meta.get("total") or 0, 2)
        self.assertEqual(meta.get("page"), 1)

        fetched = self.client.get(f"{QUOTATIONS_URL}/{a['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        fetched_data = fetched.json()["data"]
        self.assertEqual(fetched_data["id"], a["id"])
        self.assertTrue(fetched_data.get("customerName") or fetched_data.get("customer_name"))

    def test_rejects_customer_from_another_organization(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(token_a)
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        response = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token_b),
            json={"customerId": customer_a, "totalAmount": "10.00"},
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_viewer_cannot_create_quotation(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(admin)
        token = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_id, "totalAmount": "1.00"},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_quotation_created_in_org_a_is_invisible_to_org_b(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(token_a)
        create = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token_a),
            json={"customerId": customer_a, "totalAmount": "99.00"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        quote_id = create.json()["data"]["id"]
        self.created_quote_ids.append(quote_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{QUOTATIONS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(quote_id, ids_b)

        stolen = self.client.get(f"{QUOTATIONS_URL}/{quote_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        customer_b = self._create_customer(token_b)
        spoof = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token_b),
            json={
                "customerId": customer_b,
                "organizationId": "00000000-0000-0000-0000-000000000001",
                "totalAmount": "5.00",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_quote_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))
        self._assert_quote_number(spoofed.get("quoteNumber") or spoofed.get("quote_number"))


if __name__ == "__main__":
    unittest.main()
