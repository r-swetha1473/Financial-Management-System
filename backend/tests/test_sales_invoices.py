"""O2C sales invoices: delivered-DN billing, approval, RBAC, and tenant isolation."""

from __future__ import annotations

import asyncio
import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.audit_log import AuditLog
from app.models.collection import Collection
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.receivable import Receivable
from app.models.sales_invoice import SalesInvoice
from app.models.sales_order import SalesOrder
from app.models.user import User, UserSession

CUSTOMERS_URL = "/api/v1/o2c/customers"
SALES_ORDERS_URL = "/api/v1/o2c/sales-orders"
DELIVERIES_URL = "/api/v1/o2c/deliveries"
INVOICES_URL = "/api/v1/o2c/sales-invoices"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-sinv-"
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


def _approval(row: dict) -> str:
    return row.get("approvalStatus") or row.get("approval_status")


class SalesInvoiceApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_invoice_ids: list
    created_delivery_ids: list
    created_so_ids: list
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_invoice_ids = []
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
                name="Sales Invoice Isolation Org",
                slug=f"iso-sinv-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-sinv-admin",
                    email=email,
                    full_name="Sales Invoice Isolation Admin",
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
            entity_ids = list(cls.created_invoice_ids)
            if entity_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(entity_ids)))
                await session.execute(delete(Collection).where(Collection.sales_invoice_id.in_(entity_ids)))
                await session.execute(delete(Receivable).where(Receivable.source_id.in_(entity_ids)))
                await session.execute(delete(SalesInvoice).where(SalesInvoice.id.in_(entity_ids)))
            if cls.created_delivery_ids:
                await session.execute(
                    delete(SalesInvoice).where(SalesInvoice.delivery_id.in_(cls.created_delivery_ids))
                )
                await session.execute(delete(Delivery).where(Delivery.id.in_(cls.created_delivery_ids)))
            if cls.created_so_ids:
                await session.execute(delete(Delivery).where(Delivery.sales_order_id.in_(cls.created_so_ids)))
                await session.execute(delete(SalesOrder).where(SalesOrder.id.in_(cls.created_so_ids)))
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
                org_invoices = select(SalesInvoice.id).where(SalesInvoice.organization_id == cls.org_b_id)
                await session.execute(delete(Collection).where(Collection.sales_invoice_id.in_(org_invoices)))
                await session.execute(delete(Receivable).where(Receivable.organization_id == cls.org_b_id))
                await session.execute(delete(SalesInvoice).where(SalesInvoice.organization_id == cls.org_b_id))
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

    def _delivered(self, token: str, admin: str | None = None, customer_id: str | None = None) -> tuple[str, dict]:
        vendor_token = admin or token
        customer_id = customer_id or self._create_customer(vendor_token)
        so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(token),
            json={"customerId": customer_id, "status": "confirmed", "totalAmount": "100.00"},
        )
        self.assertEqual(so.status_code, 201, so.text)
        so_id = so.json()["data"]["id"]
        self.created_so_ids.append(so_id)
        dn = self.client.post(DELIVERIES_URL, headers=self._auth(token), json={"salesOrderId": so_id})
        self.assertEqual(dn.status_code, 201, dn.text)
        data = dn.json()["data"]
        self.created_delivery_ids.append(data["id"])
        return customer_id, data

    def _pending_invoice(
        self, creator: str, admin: str | None = None, amount: str = "100.00", gst: str = "18.00"
    ) -> dict:
        customer_id, delivery = self._delivered(creator, admin)
        created = self.client.post(
            INVOICES_URL,
            headers=self._auth(creator),
            json={
                "deliveryId": delivery["id"],
                "customerId": customer_id,
                "amount": amount,
                "gstAmount": gst,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        invoice = created.json()["data"]
        self.created_invoice_ids.append(invoice["id"])
        return invoice

    def _audit_count(self, invoice_id: str, action: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.entity_id == invoice_id, AuditLog.action == action)
            )

        return int(_run(_with_own_session(work)) or 0)

    def _receivable_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count()).select_from(Receivable).where(Receivable.source_id == invoice_id)
            )

        return int(_run(_with_own_session(work)) or 0)

    def test_delivered_dn_records_invoice_with_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        year = date.today().year
        customer_id, delivery = self._delivered(operator, admin)

        first = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={
                "deliveryId": delivery["id"],
                "customerId": customer_id,
                "invoiceNumber": "O2C-SHOULD-BE-IGNORED",
                "status": "paid",
                "approvalStatus": "approved",
                "amount": "24500.00",
                "gstAmount": "4410.00",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        invoice = first.json()["data"]
        self.created_invoice_ids.append(invoice["id"])
        number = invoice.get("invoiceNumber") or invoice.get("invoice_number")
        self.assertRegex(number, rf"^O2C-{year}-\d{{4}}$")
        self.assertNotEqual(number, "O2C-SHOULD-BE-IGNORED")
        self.assertEqual(invoice["status"], "pending")
        self.assertEqual(_approval(invoice), "pending")
        self.assertEqual(invoice["customerId"], customer_id)
        self.assertEqual(invoice["deliveryId"], delivery["id"])
        self.assertEqual(Decimal(str(invoice["amount"])), Decimal("24500.00"))
        self.assertEqual(Decimal(str(invoice["gstAmount"])), Decimal("4410.00"))
        self.assertEqual(Decimal(str(invoice["outstanding"])), Decimal("24500.00"))

        duplicate = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"deliveryId": delivery["id"], "amount": "10.00"},
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.text)
        self.assertIn("already has a sales invoice", duplicate.text.lower())

        _, delivery_b = self._delivered(operator, admin)
        second = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"deliveryId": delivery_b["id"], "amount": "50.00"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        invoice_b = second.json()["data"]
        self.created_invoice_ids.append(invoice_b["id"])
        number_b = invoice_b.get("invoiceNumber") or invoice_b.get("invoice_number")
        self.assertNotEqual(number, number_b)

        listed = self.client.get(f"{INVOICES_URL}?page=1&page_size=50", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(invoice["id"], ids)
        self.assertIn(invoice_b["id"], ids)

        fetched = self.client.get(f"{INVOICES_URL}/{invoice['id']}", headers=self._auth(operator))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], invoice["id"])

    def test_rejects_cancelled_delivery_and_missing_delivery(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        customer_id = self._create_customer(admin)
        so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"customerId": customer_id, "status": "confirmed", "totalAmount": "10.00"},
        )
        self.assertEqual(so.status_code, 201, so.text)
        self.created_so_ids.append(so.json()["data"]["id"])
        missing = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"deliveryId": str(uuid4()), "amount": "10.00"},
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        customer_mismatch, delivery = self._delivered(operator, admin)
        other_customer = self._create_customer(admin)
        mismatch = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"deliveryId": delivery["id"], "customerId": other_customer, "amount": "10.00"},
        )
        self.assertEqual(mismatch.status_code, 400, mismatch.text)
        self.assertIn("customer", mismatch.text.lower())
        _ = customer_mismatch

        cancelled_so = self.client.post(
            SALES_ORDERS_URL,
            headers=self._auth(operator),
            json={"customerId": self._create_customer(admin), "status": "confirmed", "totalAmount": "10.00"},
        )
        self.assertEqual(cancelled_so.status_code, 201, cancelled_so.text)
        self.created_so_ids.append(cancelled_so.json()["data"]["id"])
        cancelled_dn = self.client.post(
            DELIVERIES_URL,
            headers=self._auth(operator),
            json={"salesOrderId": cancelled_so.json()["data"]["id"], "status": "cancelled"},
        )
        self.assertEqual(cancelled_dn.status_code, 201, cancelled_dn.text)
        self.created_delivery_ids.append(cancelled_dn.json()["data"]["id"])
        cancelled_inv = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"deliveryId": cancelled_dn.json()["data"]["id"], "amount": "10.00"},
        )
        self.assertEqual(cancelled_inv.status_code, 400, cancelled_inv.text)
        self.assertIn("delivered", cancelled_inv.text.lower())

    def test_finance_approves_and_manager_rejects(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        finance = self._login("finance@demo-business.com", "finance123")
        manager = self._login("manager@demo-business.com", "manager123")
        invoice = self._pending_invoice(operator, admin)

        approved = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(finance))
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(_approval(approved.json()["data"]), "approved")
        self.assertEqual(approved.json()["data"]["status"], "pending")
        self.assertEqual(self._receivable_count(invoice["id"]), 0)
        self.assertEqual(self._audit_count(invoice["id"], "approve"), 1)

        other = self._pending_invoice(operator, admin)
        rejected = self.client.patch(f"{INVOICES_URL}/{other['id']}/reject", headers=self._auth(manager))
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(_approval(rejected.json()["data"]), "rejected")
        self.assertEqual(self._receivable_count(other["id"]), 0)
        self.assertEqual(self._audit_count(other["id"], "reject"), 1)

        again = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(finance))
        self.assertEqual(again.status_code, 400, again.text)

    def test_operator_cannot_approve_viewer_cannot_create(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        invoice = self._pending_invoice(operator, admin)

        approve = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(operator))
        self.assertEqual(approve.status_code, 403, approve.text)
        reject = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/reject", headers=self._auth(operator))
        self.assertEqual(reject.status_code, 403, reject.text)

        _, delivery = self._delivered(admin)
        created = self.client.post(
            INVOICES_URL,
            headers=self._auth(viewer),
            json={"deliveryId": delivery["id"], "amount": "10.00"},
        )
        self.assertEqual(created.status_code, 403, created.text)

    def test_org_b_cannot_see_or_invoice_org_a_delivery(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, delivery_a = self._delivered(admin_a)
        invoice_a = self.client.post(
            INVOICES_URL,
            headers=self._auth(admin_a),
            json={"deliveryId": delivery_a["id"], "amount": "10.00"},
        )
        self.assertEqual(invoice_a.status_code, 201, invoice_a.text)
        inv_id = invoice_a.json()["data"]["id"]
        self.created_invoice_ids.append(inv_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen_create = self.client.post(
            INVOICES_URL,
            headers=self._auth(token_b),
            json={"deliveryId": delivery_a["id"], "amount": "10.00"},
        )
        self.assertEqual(stolen_create.status_code, 404, stolen_create.text)
        stolen_get = self.client.get(f"{INVOICES_URL}/{inv_id}", headers=self._auth(token_b))
        self.assertEqual(stolen_get.status_code, 404, stolen_get.text)
        stolen_approve = self.client.patch(f"{INVOICES_URL}/{inv_id}/approve", headers=self._auth(token_b))
        self.assertEqual(stolen_approve.status_code, 404, stolen_approve.text)

        listed_b = self.client.get(f"{INVOICES_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(inv_id, [item["id"] for item in listed_b.json()["data"]])


if __name__ == "__main__":
    unittest.main()
