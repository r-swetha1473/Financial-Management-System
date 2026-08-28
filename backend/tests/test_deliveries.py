"""O2C delivery API: confirmed/fulfilled SO receiving, RBAC, and tenant isolation."""

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
from app.models.delivery import Delivery
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.sales_order import SalesOrder
from app.models.user import User, UserSession

CUSTOMERS_URL = "/api/v1/o2c/customers"
SALES_ORDERS_URL = "/api/v1/o2c/sales-orders"
DELIVERIES_URL = "/api/v1/o2c/deliveries"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-dn-test-"
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


class DeliveryApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_delivery_ids: list
    created_so_ids: list
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_delivery_ids = []
        cls.created_so_ids = []
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
                name="Delivery Isolation Org",
                slug=f"iso-dn-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-dn-admin",
                    email=email,
                    full_name="Delivery Isolation Admin",
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
            if cls.created_delivery_ids:
                await session.execute(delete(Delivery).where(Delivery.id.in_(cls.created_delivery_ids)))
            if cls.created_so_ids:
                await session.execute(delete(Delivery).where(Delivery.sales_order_id.in_(cls.created_so_ids)))
                await session.execute(delete(SalesOrder).where(SalesOrder.id.in_(cls.created_so_ids)))
            if cls.org_b_id is not None:
                org_sos = select(SalesOrder.id).where(SalesOrder.organization_id == cls.org_b_id)
                await session.execute(delete(Delivery).where(Delivery.sales_order_id.in_(org_sos)))
                await session.execute(delete(Delivery).where(Delivery.organization_id == cls.org_b_id))
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

    def _create_so(self, token: str, *, customer_id: str, so_status: str = "confirmed") -> dict:
        response = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(token),
            json={"customerId": customer_id, "status": so_status, "totalAmount": "100.00"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_so_ids.append(data["id"])
        return data

    def _so_status(self, token: str, so_id: str) -> str:
        fetched = self.client.get(f"{SALES_ORDERS_URL}/{so_id}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        return fetched.json()["data"]["status"]

    def test_confirmed_so_records_delivery_with_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        customer_id = self._create_customer(admin)
        year = date.today().year
        first_so = self._create_so(operator, customer_id=customer_id)

        first = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(operator),
            json={
                "salesOrderId": first_so["id"],
                "status": "delivered",
                "deliveryNumber": "DN-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        dn_a = first.json()["data"]
        self.created_delivery_ids.append(dn_a["id"])
        number_a = dn_a.get("deliveryNumber") or dn_a.get("delivery_number")
        self.assertRegex(number_a, rf"^DN-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, "DN-SHOULD-BE-IGNORED")
        self.assertEqual(dn_a["salesOrderId"], first_so["id"])
        self.assertEqual(dn_a["customerId"], customer_id)
        self.assertEqual(self._so_status(operator, first_so["id"]), "fulfilled")

        again_same = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(operator),
            json={"salesOrderId": first_so["id"]},
        )
        self.assertEqual(again_same.status_code, 201, again_same.text)
        self.created_delivery_ids.append(again_same.json()["data"]["id"])
        self.assertEqual(self._so_status(operator, first_so["id"]), "fulfilled")

        second_so = self._create_so(operator, customer_id=customer_id)
        second = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(operator),
            json={"salesOrderId": second_so["id"]},
        )
        self.assertEqual(second.status_code, 201, second.text)
        dn_b = second.json()["data"]
        self.created_delivery_ids.append(dn_b["id"])
        number_b = dn_b.get("deliveryNumber") or dn_b.get("delivery_number")
        self.assertRegex(number_b, rf"^DN-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, number_b)
        self.assertEqual(self._so_status(operator, second_so["id"]), "fulfilled")

        listed = self.client.get(f"{DELIVERIES_URL}?page=1&page_size=20", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(dn_a["id"], ids)
        self.assertIn(dn_b["id"], ids)

        fetched = self.client.get(f"{DELIVERIES_URL}/{dn_a['id']}", headers=self._auth(operator))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], dn_a["id"])

    def test_rejects_cancelled_sales_order(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        customer_id = self._create_customer(admin)
        cancelled = self._create_so(operator, customer_id=customer_id, so_status="cancelled")
        response = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(operator),
            json={"salesOrderId": cancelled["id"]},
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self._so_status(operator, cancelled["id"]), "cancelled")

    def test_rejects_sales_order_from_another_organization(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        so_a = self._create_so(admin_a, customer_id=self._create_customer(admin_a))

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(token_b),
            json={"salesOrderId": so_a["id"]},
        )
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertEqual(self._so_status(admin_a, so_a["id"]), "confirmed")

    def test_viewer_cannot_create_delivery(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        so = self._create_so(admin, customer_id=self._create_customer(admin))
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(viewer),
            json={"salesOrderId": so["id"]},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self._so_status(admin, so["id"]), "confirmed")

    def test_delivery_created_in_org_a_is_invisible_to_org_b(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        so_a = self._create_so(admin_a, customer_id=self._create_customer(admin_a))
        create = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(admin_a),
            json={"salesOrderId": so_a["id"]},
        )
        self.assertEqual(create.status_code, 201, create.text)
        dn_id = create.json()["data"]["id"]
        self.created_delivery_ids.append(dn_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{DELIVERIES_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(dn_id, [item["id"] for item in listed_b.json()["data"]])

        stolen = self.client.get(f"{DELIVERIES_URL}/{dn_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        so_b = self._create_so(token_b, customer_id=self._create_customer(token_b))
        spoof = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(token_b),
            json={
                "salesOrderId": so_b["id"],
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_delivery_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))


if __name__ == "__main__":
    unittest.main()
