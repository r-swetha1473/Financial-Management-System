"""O2C sales-order API: accepted-quotation conversion, RBAC, and tenant isolation."""

from __future__ import annotations

import asyncio
import unittest
from datetime import date
from decimal import Decimal
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
from app.models.sales_order import SalesOrder
from app.models.user import User, UserSession

CUSTOMERS_URL = "/api/v1/o2c/customers"
QUOTATIONS_URL = "/api/v1/o2c/quotations"
SALES_ORDERS_URL = "/api/v1/o2c/sales-orders"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-so-test-"
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


class SalesOrderApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_so_ids: list
    created_quote_ids: list
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_so_ids = []
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
                name="SO Isolation Org",
                slug=f"iso-so-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-so-admin",
                    email=email,
                    full_name="SO Isolation Admin",
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
            if cls.created_so_ids:
                await session.execute(delete(SalesOrder).where(SalesOrder.id.in_(cls.created_so_ids)))
            if cls.created_quote_ids:
                quote_ids = cls.created_quote_ids
                await session.execute(delete(SalesOrder).where(SalesOrder.quotation_id.in_(quote_ids)))
                await session.execute(delete(Quotation).where(Quotation.id.in_(quote_ids)))
            if cls.org_b_id is not None:
                await session.execute(delete(SalesOrder).where(SalesOrder.organization_id == cls.org_b_id))
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

    def _create_customer(self, token: str) -> str:
        response = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}{uuid4().hex[:8]}"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        customer_id = response.json()["data"]["id"]
        self.created_customer_ids.append(customer_id)
        return customer_id

    def _create_quotation(self, token: str, *, customer_id: str, quote_status: str) -> dict:
        response = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_id, "status": quote_status, "totalAmount": "100.00"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_quote_ids.append(data["id"])
        return data

    def _quote_status(self, token: str, quote_id: str) -> str:
        fetched = self.client.get(f"{QUOTATIONS_URL}/{quote_id}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        return fetched.json()["data"]["status"]

    def test_accepted_quotation_converts_to_so_with_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        customer_id = self._create_customer(admin)
        year = date.today().year

        first_quote = self._create_quotation(operator, customer_id=customer_id, quote_status="accepted")
        first = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={
                "quotationId": first_quote["id"],
                "customerId": customer_id,
                "totalAmount": "24500.00",
                "status": "confirmed",
                "orderNumber": "SO-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        so_a = first.json()["data"]
        self.created_so_ids.append(so_a["id"])
        number_a = so_a.get("orderNumber") or so_a.get("order_number")
        self.assertRegex(number_a, rf"^SO-{year}-\d{{3}}$")
        self.assertNotEqual(number_a, "SO-SHOULD-BE-IGNORED")
        self.assertEqual(so_a["quotationId"], first_quote["id"])
        self.assertEqual(so_a["customerId"], customer_id)
        self.assertEqual(so_a["status"], "confirmed")
        self.assertEqual(self._quote_status(operator, first_quote["id"]), "converted")
        self.assertEqual(Decimal(str(so_a.get("totalAmount") or so_a.get("total_amount"))), Decimal("24500.00"))

        second_quote = self._create_quotation(operator, customer_id=customer_id, quote_status="accepted")
        second = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": second_quote["id"], "customerId": customer_id, "totalAmount": "12800.00"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        so_b = second.json()["data"]
        self.created_so_ids.append(so_b["id"])
        number_b = so_b.get("orderNumber") or so_b.get("order_number")
        self.assertRegex(number_b, rf"^SO-{year}-\d{{3}}$")
        self.assertNotEqual(number_a, number_b)
        self.assertEqual(self._quote_status(operator, second_quote["id"]), "converted")

        listed = self.client.get(f"{SALES_ORDERS_URL}?page=1&page_size=20", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(so_a["id"], ids)
        self.assertIn(so_b["id"], ids)

        fetched = self.client.get(f"{SALES_ORDERS_URL}/{so_a['id']}", headers=self._auth(operator))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], so_a["id"])
        self.assertTrue(fetched.json()["data"].get("quoteNumber") or fetched.json()["data"].get("quote_number"))

        direct = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"customerId": customer_id, "totalAmount": "50.00"},
        )
        self.assertEqual(direct.status_code, 201, direct.text)
        self.created_so_ids.append(direct.json()["data"]["id"])
        self.assertIsNone(direct.json()["data"].get("quotationId") or direct.json()["data"].get("quotation_id"))

    def test_rejects_draft_and_converted_quotations(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        customer_id = self._create_customer(admin)

        draft = self._create_quotation(operator, customer_id=customer_id, quote_status="draft")
        draft_so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": draft["id"], "customerId": customer_id},
        )
        self.assertEqual(draft_so.status_code, 400, draft_so.text)
        self.assertEqual(self._quote_status(operator, draft["id"]), "draft")

        accepted = self._create_quotation(operator, customer_id=customer_id, quote_status="accepted")
        created = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": accepted["id"], "customerId": customer_id},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.created_so_ids.append(created.json()["data"]["id"])
        self.assertEqual(self._quote_status(operator, accepted["id"]), "converted")

        again = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": accepted["id"], "customerId": customer_id},
        )
        self.assertEqual(again.status_code, 400, again.text)

    def test_rejects_quotation_from_another_organization(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(admin_a)
        quote_a = self._create_quotation(admin_a, customer_id=customer_a, quote_status="accepted")

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        customer_b = self._create_customer(token_b)
        stolen = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(token_b),
            json={"quotationId": quote_a["id"], "customerId": customer_b},
        )
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertEqual(self._quote_status(admin_a, quote_a["id"]), "accepted")

    def test_viewer_cannot_create_sales_order(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(admin)
        quote = self._create_quotation(admin, customer_id=customer_id, quote_status="accepted")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(viewer),
            json={"quotationId": quote["id"], "customerId": customer_id},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self._quote_status(admin, quote["id"]), "accepted")

    def test_sales_order_created_in_org_a_is_invisible_to_org_b(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(admin_a)
        quote_a = self._create_quotation(admin_a, customer_id=customer_a, quote_status="accepted")
        create = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(admin_a),
            json={"quotationId": quote_a["id"], "customerId": customer_a, "totalAmount": "10.00"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        so_id = create.json()["data"]["id"]
        self.created_so_ids.append(so_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{SALES_ORDERS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(so_id, [item["id"] for item in listed_b.json()["data"]])

        stolen = self.client.get(f"{SALES_ORDERS_URL}/{so_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        customer_b = self._create_customer(token_b)
        quote_b = self._create_quotation(token_b, customer_id=customer_b, quote_status="accepted")
        spoof = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(token_b),
            json={
                "quotationId": quote_b["id"],
                "customerId": customer_b,
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_so_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))


if __name__ == "__main__":
    unittest.main()
