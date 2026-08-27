"""O2C collections: approved-invoice gate, receivable lock, live outstanding, concurrency."""

from __future__ import annotations

import asyncio
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
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
COLLECTIONS_URL = "/api/v1/o2c/collections"
RECEIVABLES_URL = "/api/v1/o2c/receivables"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-col-"
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


class CollectionApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_collection_ids: list
    created_invoice_ids: list
    created_delivery_ids: list
    created_so_ids: list
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_collection_ids = []
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
                name="Collection Isolation Org",
                slug=f"iso-col-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-col-admin",
                    email=email,
                    full_name="Collection Isolation Admin",
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
            entity_ids = list(cls.created_collection_ids) + list(cls.created_invoice_ids)
            if entity_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(entity_ids)))
            if cls.created_invoice_ids:
                await session.execute(
                    delete(Collection).where(Collection.sales_invoice_id.in_(cls.created_invoice_ids))
                )
                await session.execute(delete(Receivable).where(Receivable.source_id.in_(cls.created_invoice_ids)))
                await session.execute(delete(SalesInvoice).where(SalesInvoice.id.in_(cls.created_invoice_ids)))
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

    def _delivered(self, token: str, admin: str | None = None) -> tuple[str, dict]:
        vendor_token = admin or token
        customer_id = self._create_customer(vendor_token)
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

    def _approved_invoice(self, amount: str = "100.00", gst: str = "18.00") -> tuple[str, dict]:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        finance = self._login("finance@demo-business.com", "finance123")
        invoice = self._pending_invoice(operator, admin, amount=amount, gst=gst)
        approved = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(finance))
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(_approval(approved.json()["data"]), "approved")
        return operator, approved.json()["data"]

    def _collect(self, token: str, invoice_id: str, amount: str, extra: dict | None = None):
        body = {
            "salesInvoiceId": invoice_id,
            "amount": amount,
            "paymentMode": "UPI",
            "collectionDate": date.today().isoformat(),
            "status": "cancelled",
            "organizationId": "00000000-0000-0000-0000-999999999999",
        }
        if extra:
            body.update(extra)
        return self.client.post(COLLECTIONS_URL, headers=self._auth(token), json=body)

    def _track_collection(self, response) -> dict:
        data = response.json()["data"]
        self.created_collection_ids.append(data["id"])
        return data

    def _receivable(self, invoice_id: str) -> dict | None:
        async def work(session: AsyncSession):
            row = await session.scalar(
                select(Receivable).where(
                    Receivable.source_type == "sales_invoice",
                    Receivable.source_id == invoice_id,
                )
            )
            if row is None:
                return None
            return {
                "amount": Decimal(str(row.amount)),
                "outstanding": Decimal(str(row.outstanding)),
                "status": row.status,
            }

        return _run(_with_own_session(work))

    def _receivable_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count()).select_from(Receivable).where(
                    Receivable.source_type == "sales_invoice",
                    Receivable.source_id == invoice_id,
                )
            )

        return int(_run(_with_own_session(work)) or 0)

    def _invoice_row(self, invoice_id: str) -> dict:
        async def work(session: AsyncSession):
            row = await session.get(SalesInvoice, invoice_id)
            return {
                "status": row.status,
                "approval_status": row.approval_status,
                "amount": Decimal(str(row.amount)),
            }

        return _run(_with_own_session(work))

    def _collection_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count()).select_from(Collection).where(Collection.sales_invoice_id == invoice_id)
            )

        return int(_run(_with_own_session(work)) or 0)

    def _completed_sum(self, invoice_id: str) -> Decimal:
        async def work(session: AsyncSession):
            paid = await session.scalar(
                select(func.coalesce(func.sum(Collection.amount), 0)).where(
                    Collection.sales_invoice_id == invoice_id,
                    Collection.status == "completed",
                )
            )
            return Decimal(str(paid or 0))

        return _run(_with_own_session(work))

    def _finance_txn_count(self, organization_id: str | None = None) -> int:
        async def work(session: AsyncSession):
            if organization_id:
                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM finance_transactions "
                        "WHERE organization_id = CAST(:oid AS uuid)"
                    ),
                    {"oid": organization_id},
                )
            else:
                result = await session.execute(text("SELECT COUNT(*) FROM finance_transactions"))
            return result.scalar()

        return int(_run(_with_own_session(work)) or 0)

    def _audit_count(self, entity_id: str, action: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.entity_id == entity_id, AuditLog.action == action)
            )

        return int(_run(_with_own_session(work)) or 0)

    def test_happy_path_creates_receivable_and_records_collection(self) -> None:
        token, invoice = self._approved_invoice(amount="24500.00", gst="4410.00")
        finance_before = self._finance_txn_count(invoice["organizationId"])

        response = self._collect(token, invoice["id"], "5000.00")
        self.assertEqual(response.status_code, 201, response.text)
        collection = self._track_collection(response)
        self.assertNotIn("collectionNumber", collection)
        self.assertNotIn("collection_number", collection)
        self.assertEqual(collection["status"], "completed")
        self.assertEqual(Decimal(str(collection["amount"])), Decimal("5000.00"))
        self.assertEqual(collection["salesInvoiceId"], invoice["id"])
        self.assertEqual(collection["invoiceNumber"], invoice.get("invoiceNumber") or invoice.get("invoice_number"))

        receivable = self._receivable(invoice["id"])
        self.assertIsNotNone(receivable)
        self.assertEqual(receivable["amount"], Decimal("24500.00"))
        self.assertEqual(receivable["outstanding"], Decimal("19500.00"))
        self.assertEqual(receivable["status"], "partial")
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "partially_paid")
        self.assertEqual(self._audit_count(collection["id"], "create"), 1)
        self.assertEqual(self._finance_txn_count(invoice["organizationId"]), finance_before)

        listed = self.client.get(f"{COLLECTIONS_URL}?page=1&page_size=50", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(collection["id"], [item["id"] for item in listed.json()["data"]])

        receivables = self.client.get(f"{RECEIVABLES_URL}?page=1&page_size=50", headers=self._auth(token))
        self.assertEqual(receivables.status_code, 200, receivables.text)
        match = next(item for item in receivables.json()["data"] if item["sourceId"] == invoice["id"])
        self.assertEqual(Decimal(str(match["outstanding"])), Decimal("19500.00"))

    def test_rejects_collection_against_pending_invoice(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        invoice = self._pending_invoice(operator, admin)
        response = self._collect(operator, invoice["id"], "10.00")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("approved", response.text.lower())
        self.assertIsNone(self._receivable(invoice["id"]))
        self.assertEqual(self._collection_count(invoice["id"]), 0)

    def test_rejects_over_outstanding_and_leaves_receivable_unchanged(self) -> None:
        token, invoice = self._approved_invoice()
        first = self._collect(token, invoice["id"], "40.00")
        self.assertEqual(first.status_code, 201, first.text)
        self._track_collection(first)
        before = self._receivable(invoice["id"])
        self.assertEqual(before["outstanding"], Decimal("60.00"))
        self.assertEqual(before["status"], "partial")

        over = self._collect(token, invoice["id"], "60.01")
        self.assertEqual(over.status_code, 400, over.text)
        self.assertIn("outstanding", over.text.lower())
        after = self._receivable(invoice["id"])
        self.assertEqual(after["outstanding"], Decimal("60.00"))
        self.assertEqual(after["status"], "partial")
        self.assertEqual(self._collection_count(invoice["id"]), 1)
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("40.00"))

    def test_partial_then_closing_collection_transitions_status(self) -> None:
        token, invoice = self._approved_invoice()
        first = self._collect(token, invoice["id"], "40.00")
        self.assertEqual(first.status_code, 201, first.text)
        self._track_collection(first)
        after_first = self._receivable(invoice["id"])
        self.assertEqual(after_first["status"], "partial")
        self.assertEqual(after_first["outstanding"], Decimal("60.00"))
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "partially_paid")

        second = self._collect(token, invoice["id"], "60.00")
        self.assertEqual(second.status_code, 201, second.text)
        self._track_collection(second)
        after_second = self._receivable(invoice["id"])
        self.assertEqual(after_second["status"], "closed")
        self.assertEqual(after_second["outstanding"], Decimal("0.00"))
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "paid")
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("100.00"))

    def test_concurrent_first_collections_create_exactly_one_receivable(self) -> None:
        """INSERT ON CONFLICT + FOR UPDATE on a brand-new invoice with no receivable row."""
        token, invoice = self._approved_invoice()
        self.assertIsNone(self._receivable(invoice["id"]))
        self.assertEqual(self._receivable_count(invoice["id"]), 0)

        barrier = threading.Barrier(2)

        def post_once():
            barrier.wait(timeout=10)
            return self._collect(token, invoice["id"], "80.00")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(post_once)
            second = pool.submit(post_once)
            results = [first.result(timeout=30), second.result(timeout=30)]

        self.assertTrue(
            all(row.status_code < 500 for row in results),
            [row.text for row in results],
        )
        codes = sorted(row.status_code for row in results)
        self.assertEqual(codes, [201, 400], [row.text for row in results])
        success = next(row for row in results if row.status_code == 201)
        failure = next(row for row in results if row.status_code == 400)
        self._track_collection(success)
        self.assertIn("outstanding", failure.text.lower())

        self.assertEqual(self._receivable_count(invoice["id"]), 1)
        receivable = self._receivable(invoice["id"])
        self.assertIsNotNone(receivable)
        self.assertEqual(receivable["outstanding"], Decimal("20.00"))
        self.assertEqual(receivable["status"], "partial")
        self.assertEqual(self._collection_count(invoice["id"]), 1)
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("80.00"))

    def test_concurrent_collections_against_existing_receivable(self) -> None:
        """Two concurrent collections against one already-locked receivable; only one can succeed."""
        token, invoice = self._approved_invoice()
        seed = self._collect(token, invoice["id"], "20.00")
        self.assertEqual(seed.status_code, 201, seed.text)
        self._track_collection(seed)
        self.assertEqual(self._receivable(invoice["id"])["outstanding"], Decimal("80.00"))

        barrier = threading.Barrier(2)

        def post_once():
            barrier.wait(timeout=10)
            return self._collect(token, invoice["id"], "80.00")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(post_once)
            second = pool.submit(post_once)
            results = [first.result(timeout=30), second.result(timeout=30)]

        self.assertTrue(
            all(row.status_code < 500 for row in results),
            [row.text for row in results],
        )
        codes = sorted(row.status_code for row in results)
        self.assertEqual(codes, [201, 400], [row.text for row in results])
        success = next(row for row in results if row.status_code == 201)
        self._track_collection(success)

        self.assertEqual(self._receivable_count(invoice["id"]), 1)
        receivable = self._receivable(invoice["id"])
        self.assertEqual(receivable["outstanding"], Decimal("0.00"))
        self.assertEqual(receivable["status"], "closed")
        self.assertEqual(self._collection_count(invoice["id"]), 2)
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("100.00"))

    def test_viewer_cannot_create_collection(self) -> None:
        token, invoice = self._approved_invoice()
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self._collect(viewer, invoice["id"], "10.00")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIsNone(self._receivable(invoice["id"]))

    def test_org_b_cannot_collect_org_a_invoice(self) -> None:
        token_a, invoice_a = self._approved_invoice()
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self._collect(token_b, invoice_a["id"], "10.00")
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertIsNone(self._receivable(invoice_a["id"]))

        admin_b = token_b
        invoice_b = self._pending_invoice(admin_b, amount="100.00", gst="0")
        approved_b = self.client.patch(f"{INVOICES_URL}/{invoice_b['id']}/approve", headers=self._auth(admin_b))
        self.assertEqual(approved_b.status_code, 200, approved_b.text)
        paid_b = self._collect(
            admin_b,
            invoice_b["id"],
            "25.00",
            extra={"organizationId": "00000000-0000-0000-0000-000000000001"},
        )
        self.assertEqual(paid_b.status_code, 201, paid_b.text)
        collection_b = self._track_collection(paid_b)
        self.assertEqual(collection_b["organizationId"], str(self.org_b_id))

        listed_b = self.client.get(f"{COLLECTIONS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertIn(collection_b["id"], ids_b)

        listed_a = self.client.get(f"{COLLECTIONS_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed_a.status_code, 200, listed_a.text)
        self.assertNotIn(collection_b["id"], [item["id"] for item in listed_a.json()["data"]])


if __name__ == "__main__":
    unittest.main()
