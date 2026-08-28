"""O2C quotation API: sequence numbers, customer tenancy, RBAC, and isolation."""

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

QUOTATIONS_URL = "/api/v1/o2c/quotations"
CUSTOMERS_URL = "/api/v1/o2c/customers"
SALES_ORDERS_URL = "/api/v1/o2c/sales-orders"
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
                await session.execute(delete(SalesOrder).where(SalesOrder.quotation_id.in_(cls.created_quote_ids)))
                await session.execute(delete(Quotation).where(Quotation.id.in_(cls.created_quote_ids)))
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
        self.assertRegex(value, rf"^Q-{year}-\d{{3,}}$")

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
        self.assertIsNone(a.get("planDuration") if "planDuration" in a else a.get("plan_duration"))
        self.assertIsNone(a.get("billingCycle") if "billingCycle" in a else a.get("billing_cycle"))
        self.assertEqual(Decimal(str(a.get("depositAmount") or a.get("deposit_amount") or "0")), Decimal("0"))

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

    def test_list_filters_by_customer_and_status(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(admin)
        customer_b = self._create_customer(admin)
        token = self._login("operator@demo-business.com", "operator123")

        draft_a = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_a, "status": "draft", "totalAmount": "10.00"},
        )
        sent_a = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_a, "status": "sent", "totalAmount": "20.00"},
        )
        draft_b = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={"customerId": customer_b, "status": "draft", "totalAmount": "30.00"},
        )
        self.assertEqual(draft_a.status_code, 201, draft_a.text)
        self.assertEqual(sent_a.status_code, 201, sent_a.text)
        self.assertEqual(draft_b.status_code, 201, draft_b.text)
        id_draft_a = draft_a.json()["data"]["id"]
        id_sent_a = sent_a.json()["data"]["id"]
        id_draft_b = draft_b.json()["data"]["id"]
        self.created_quote_ids.extend([id_draft_a, id_sent_a, id_draft_b])

        filtered = self.client.get(
            f"{QUOTATIONS_URL}?page=1&page_size=20&customer_id={customer_a}&status=draft",
            headers=self._auth(token),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        body = filtered.json()
        ids = [item["id"] for item in body["data"]]
        self.assertEqual(ids, [id_draft_a])
        self.assertEqual(body["meta"].get("total"), 1)
        self.assertNotIn(id_sent_a, ids)
        self.assertNotIn(id_draft_b, ids)

    def test_list_filters_stay_tenant_scoped(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        customer_a = self._create_customer(token_a)
        create_a = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token_a),
            json={"customerId": customer_a, "status": "draft", "totalAmount": "11.00"},
        )
        self.assertEqual(create_a.status_code, 201, create_a.text)
        quote_a = create_a.json()["data"]["id"]
        self.created_quote_ids.append(quote_a)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        customer_b = self._create_customer(token_b)
        create_b = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token_b),
            json={"customerId": customer_b, "status": "draft", "totalAmount": "22.00"},
        )
        self.assertEqual(create_b.status_code, 201, create_b.text)
        quote_b = create_b.json()["data"]["id"]
        self.created_quote_ids.append(quote_b)

        stolen = self.client.get(
            f"{QUOTATIONS_URL}?page=1&page_size=20&customer_id={customer_a}&status=draft",
            headers=self._auth(token_b),
        )
        self.assertEqual(stolen.status_code, 200, stolen.text)
        stolen_ids = [item["id"] for item in stolen.json()["data"]]
        self.assertNotIn(quote_a, stolen_ids)

        own = self.client.get(
            f"{QUOTATIONS_URL}?page=1&page_size=20&customer_id={customer_b}&status=draft",
            headers=self._auth(token_b),
        )
        self.assertEqual(own.status_code, 200, own.text)
        own_ids = [item["id"] for item in own.json()["data"]]
        self.assertEqual(own_ids, [quote_b])
        self.assertNotIn(quote_a, own_ids)

    def test_create_persists_plan_duration_billing_cycle_and_deposit(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(admin)
        token = self._login("operator@demo-business.com", "operator123")
        create = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(token),
            json={
                "customerId": customer_id,
                "totalAmount": "4500.00",
                "planDuration": 90,
                "billingCycle": "monthly",
                "depositAmount": "15000.00",
                "status": "accepted",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()["data"]
        self.created_quote_ids.append(created["id"])
        self.assertEqual(created.get("planDuration") or created.get("plan_duration"), 90)
        self.assertEqual(created.get("billingCycle") or created.get("billing_cycle"), "monthly")
        self.assertEqual(Decimal(str(created.get("depositAmount") or created.get("deposit_amount"))), Decimal("15000.0000"))
        self.assertEqual(created.get("totalAmount") or created.get("total_amount"), "4500.0000")

        fetched = self.client.get(f"{QUOTATIONS_URL}/{created['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        data = fetched.json()["data"]
        self.assertEqual(data.get("planDuration") or data.get("plan_duration"), 90)
        self.assertEqual(data.get("billingCycle") or data.get("billing_cycle"), "monthly")
        self.assertEqual(Decimal(str(data.get("depositAmount") or data.get("deposit_amount"))), Decimal("15000.0000"))

    def test_finance_can_accept_draft_plan_then_convert_to_sales_order(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        finance = self._login("finance@demo-business.com", "finance123")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        customer_id = self._create_customer(admin)

        created = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(operator),
            json={"customerId": customer_id, "totalAmount": "800.00", "status": "draft"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        quote_id = created.json()["data"]["id"]
        self.created_quote_ids.append(quote_id)

        blocked_so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": quote_id, "customerId": customer_id, "totalAmount": "800.00"},
        )
        self.assertEqual(blocked_so.status_code, 400, blocked_so.text)

        operator_accept = self.client.patch(f"{QUOTATIONS_URL}/{quote_id}/accept", headers=self._auth(operator))
        self.assertEqual(operator_accept.status_code, 403, operator_accept.text)
        viewer_accept = self.client.patch(f"{QUOTATIONS_URL}/{quote_id}/accept", headers=self._auth(viewer))
        self.assertEqual(viewer_accept.status_code, 403, viewer_accept.text)

        accepted = self.client.patch(f"{QUOTATIONS_URL}/{quote_id}/accept", headers=self._auth(finance))
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["data"]["status"], "accepted")

        again = self.client.patch(f"{QUOTATIONS_URL}/{quote_id}/accept", headers=self._auth(finance))
        self.assertEqual(again.status_code, 400, again.text)

        sent = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(operator),
            json={"customerId": customer_id, "status": "sent"},
        )
        self.assertEqual(sent.status_code, 201, sent.text)
        sent_id = sent.json()["data"]["id"]
        self.created_quote_ids.append(sent_id)
        wrong_status = self.client.patch(f"{QUOTATIONS_URL}/{sent_id}/accept", headers=self._auth(finance))
        self.assertEqual(wrong_status.status_code, 400, wrong_status.text)

        reject_me = self.client.post(
            QUOTATIONS_URL,
            headers=self._auth(operator),
            json={"customerId": customer_id, "status": "draft"},
        )
        self.assertEqual(reject_me.status_code, 201, reject_me.text)
        reject_id = reject_me.json()["data"]["id"]
        self.created_quote_ids.append(reject_id)
        rejected = self.client.patch(f"{QUOTATIONS_URL}/{reject_id}/reject", headers=self._auth(finance))
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["data"]["status"], "rejected")

        so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"quotationId": quote_id, "customerId": customer_id, "totalAmount": "800.00"},
        )
        self.assertEqual(so.status_code, 201, so.text)
        self.assertEqual(so.json()["data"]["quotationId"], quote_id)

        missing = self.client.patch(
            f"{QUOTATIONS_URL}/00000000-0000-0000-0000-000000000099/accept",
            headers=self._auth(finance),
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.patch(f"{QUOTATIONS_URL}/{quote_id}/accept", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)


if __name__ == "__main__":
    unittest.main()
