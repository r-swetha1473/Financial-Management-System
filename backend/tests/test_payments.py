"""P2P payments: approved-invoice gate, payable lock, live outstanding, concurrency."""

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
from app.models.goods_receipt import GoodsReceipt
from app.models.organization import Organization
from app.models.payable import Payable
from app.models.payment import Payment
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_request import PurchaseRequest
from app.models.supplier_invoice import SupplierInvoice
from app.models.user import User, UserSession
from app.models.vendor import Vendor

VENDORS_URL = "/api/v1/p2p/vendors"
PRS_URL = "/api/v1/p2p/purchase-requests"
POS_URL = "/api/v1/p2p/purchase-orders"
GRNS_URL = "/api/v1/p2p/goods-receipts"
INVOICES_URL = "/api/v1/p2p/supplier-invoices"
PAYMENTS_URL = "/api/v1/p2p/payments"
PAYABLES_URL = "/api/v1/p2p/payables"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-pay-"
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


class PaymentApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_payment_ids: list
    created_invoice_ids: list
    created_grn_ids: list
    created_po_ids: list
    created_pr_ids: list
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_payment_ids = []
        cls.created_invoice_ids = []
        cls.created_grn_ids = []
        cls.created_po_ids = []
        cls.created_pr_ids = []
        cls.created_vendor_ids = []
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
                name="Payment Isolation Org",
                slug=f"iso-pay-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-pay-admin",
                    email=email,
                    full_name="Payment Isolation Admin",
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
            entity_ids = list(cls.created_payment_ids) + list(cls.created_invoice_ids)
            if entity_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(entity_ids)))
            if cls.created_invoice_ids:
                await session.execute(
                    delete(Payment).where(Payment.supplier_invoice_id.in_(cls.created_invoice_ids))
                )
                await session.execute(delete(Payable).where(Payable.source_id.in_(cls.created_invoice_ids)))
                await session.execute(delete(SupplierInvoice).where(SupplierInvoice.id.in_(cls.created_invoice_ids)))
            if cls.created_grn_ids:
                await session.execute(
                    delete(SupplierInvoice).where(SupplierInvoice.goods_receipt_id.in_(cls.created_grn_ids))
                )
                await session.execute(delete(GoodsReceipt).where(GoodsReceipt.id.in_(cls.created_grn_ids)))
            if cls.created_po_ids:
                await session.execute(delete(GoodsReceipt).where(GoodsReceipt.purchase_order_id.in_(cls.created_po_ids)))
                await session.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(cls.created_po_ids)))
            if cls.created_pr_ids:
                await session.execute(delete(PurchaseRequest).where(PurchaseRequest.id.in_(cls.created_pr_ids)))
            await session.execute(delete(PurchaseRequest).where(PurchaseRequest.notes.like(f"{TEST_MARKER}%")))
            if cls.created_vendor_ids:
                await session.execute(delete(Vendor).where(Vendor.id.in_(cls.created_vendor_ids)))
            await session.execute(delete(Vendor).where(Vendor.name.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
                await session.execute(delete(Payment).where(Payment.organization_id == cls.org_b_id))
                await session.execute(delete(Payable).where(Payable.organization_id == cls.org_b_id))
                await session.execute(delete(SupplierInvoice).where(SupplierInvoice.organization_id == cls.org_b_id))
                await session.execute(delete(GoodsReceipt).where(GoodsReceipt.organization_id == cls.org_b_id))
                await session.execute(delete(PurchaseOrder).where(PurchaseOrder.organization_id == cls.org_b_id))
                await session.execute(delete(PurchaseRequest).where(PurchaseRequest.organization_id == cls.org_b_id))
                await session.execute(delete(Vendor).where(Vendor.organization_id == cls.org_b_id))
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

    def _create_vendor(self, token: str) -> str:
        response = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}{uuid4().hex[:8]}", "status": "active"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        vendor_id = response.json()["data"]["id"]
        self.created_vendor_ids.append(vendor_id)
        return vendor_id

    def _received_grn(self, token: str, admin: str | None = None, vendor_id: str | None = None) -> tuple[str, dict]:
        vendor_token = admin or token
        vendor_id = vendor_id or self._create_vendor(vendor_token)
        pr = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"vendorId": vendor_id, "status": "approved", "notes": f"{TEST_MARKER}{uuid4().hex[:6]}"},
        )
        self.assertEqual(pr.status_code, 201, pr.text)
        pr_id = pr.json()["data"]["id"]
        self.created_pr_ids.append(pr_id)
        po = self.client.post(
            POS_URL,
            headers=self._auth(token),
            json={"purchaseRequestId": pr_id, "vendorId": vendor_id, "status": "issued", "totalAmount": "100.00"},
        )
        self.assertEqual(po.status_code, 201, po.text)
        po_id = po.json()["data"]["id"]
        self.created_po_ids.append(po_id)
        grn = self.client.post(GRNS_URL, headers=self._auth(token), json={"purchaseOrderId": po_id})
        self.assertEqual(grn.status_code, 201, grn.text)
        data = grn.json()["data"]
        self.created_grn_ids.append(data["id"])
        return vendor_id, data

    def _pending_invoice(self, creator: str, admin: str | None = None, amount: str = "100.00", gst: str = "18.00") -> dict:
        vendor_id, grn = self._received_grn(creator, admin)
        created = self.client.post(
            INVOICES_URL,
            headers=self._auth(creator),
            json={"goodsReceiptId": grn["id"], "vendorId": vendor_id, "amount": amount, "gstAmount": gst},
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

    def _pay(self, token: str, invoice_id: str, amount: str, extra: dict | None = None):
        body = {
            "supplierInvoiceId": invoice_id,
            "amount": amount,
            "paymentMode": "UPI",
            "paymentDate": date.today().isoformat(),
            "status": "cancelled",
            "organizationId": "00000000-0000-0000-0000-999999999999",
        }
        if extra:
            body.update(extra)
        return self.client.post(PAYMENTS_URL, headers=self._auth(token), json=body)

    def _track_payment(self, response) -> dict:
        data = response.json()["data"]
        self.created_payment_ids.append(data["id"])
        return data

    def _payable(self, invoice_id: str) -> dict | None:
        async def work(session: AsyncSession):
            row = await session.scalar(
                select(Payable).where(
                    Payable.source_type == "supplier_invoice",
                    Payable.source_id == invoice_id,
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

    def _payable_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count()).select_from(Payable).where(
                    Payable.source_type == "supplier_invoice",
                    Payable.source_id == invoice_id,
                )
            )

        return int(_run(_with_own_session(work)) or 0)

    def _invoice_row(self, invoice_id: str) -> dict:
        async def work(session: AsyncSession):
            row = await session.get(SupplierInvoice, invoice_id)
            return {
                "status": row.status,
                "approval_status": row.approval_status,
                "amount": Decimal(str(row.amount)),
            }

        return _run(_with_own_session(work))

    def _payment_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count()).select_from(Payment).where(Payment.supplier_invoice_id == invoice_id)
            )

        return int(_run(_with_own_session(work)) or 0)

    def _completed_sum(self, invoice_id: str) -> Decimal:
        async def work(session: AsyncSession):
            paid = await session.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.supplier_invoice_id == invoice_id,
                    Payment.status == "completed",
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

    def test_happy_path_creates_payable_and_records_payment(self) -> None:
        token, invoice = self._approved_invoice(amount="24500.00", gst="4410.00")
        finance_before = self._finance_txn_count(invoice["organizationId"])

        response = self._pay(token, invoice["id"], "5000.00")
        self.assertEqual(response.status_code, 201, response.text)
        payment = self._track_payment(response)
        self.assertNotIn("paymentNumber", payment)
        self.assertNotIn("payment_number", payment)
        self.assertEqual(payment["status"], "completed")
        self.assertEqual(Decimal(str(payment["amount"])), Decimal("5000.00"))
        self.assertEqual(payment["supplierInvoiceId"], invoice["id"])
        self.assertEqual(payment["invoiceNumber"], invoice.get("invoiceNumber") or invoice.get("invoice_number"))

        payable = self._payable(invoice["id"])
        self.assertIsNotNone(payable)
        self.assertEqual(payable["amount"], Decimal("24500.00"))
        self.assertEqual(payable["outstanding"], Decimal("19500.00"))
        self.assertEqual(payable["status"], "partial")
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "partially_paid")
        self.assertEqual(self._audit_count(payment["id"], "create"), 1)
        self.assertEqual(self._finance_txn_count(invoice["organizationId"]), finance_before)

        listed = self.client.get(f"{PAYMENTS_URL}?page=1&page_size=50", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(payment["id"], [item["id"] for item in listed.json()["data"]])

    def test_rejects_payment_against_pending_invoice(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        invoice = self._pending_invoice(operator, admin)
        response = self._pay(operator, invoice["id"], "10.00")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("approved", response.text.lower())
        self.assertIsNone(self._payable(invoice["id"]))
        self.assertEqual(self._payment_count(invoice["id"]), 0)

    def test_rejects_over_outstanding_and_leaves_payable_unchanged(self) -> None:
        token, invoice = self._approved_invoice()
        first = self._pay(token, invoice["id"], "40.00")
        self.assertEqual(first.status_code, 201, first.text)
        self._track_payment(first)
        before = self._payable(invoice["id"])
        self.assertEqual(before["outstanding"], Decimal("60.00"))
        self.assertEqual(before["status"], "partial")

        over = self._pay(token, invoice["id"], "60.01")
        self.assertEqual(over.status_code, 400, over.text)
        self.assertIn("outstanding", over.text.lower())
        after = self._payable(invoice["id"])
        self.assertEqual(after["outstanding"], Decimal("60.00"))
        self.assertEqual(after["status"], "partial")
        self.assertEqual(self._payment_count(invoice["id"]), 1)
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("40.00"))

    def test_partial_then_closing_payment_transitions_status(self) -> None:
        token, invoice = self._approved_invoice()
        first = self._pay(token, invoice["id"], "40.00")
        self.assertEqual(first.status_code, 201, first.text)
        self._track_payment(first)
        after_first = self._payable(invoice["id"])
        self.assertEqual(after_first["status"], "partial")
        self.assertEqual(after_first["outstanding"], Decimal("60.00"))
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "partially_paid")

        second = self._pay(token, invoice["id"], "60.00")
        self.assertEqual(second.status_code, 201, second.text)
        self._track_payment(second)
        after_second = self._payable(invoice["id"])
        self.assertEqual(after_second["status"], "closed")
        self.assertEqual(after_second["outstanding"], Decimal("0.00"))
        self.assertEqual(self._invoice_row(invoice["id"])["status"], "paid")
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("100.00"))

    def test_concurrent_first_payments_create_exactly_one_payable(self) -> None:
        """INSERT ON CONFLICT + FOR UPDATE on a brand-new invoice with no payable row."""
        token, invoice = self._approved_invoice()
        self.assertIsNone(self._payable(invoice["id"]))
        self.assertEqual(self._payable_count(invoice["id"]), 0)

        barrier = threading.Barrier(2)

        def post_once():
            barrier.wait(timeout=10)
            return self._pay(token, invoice["id"], "80.00")

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
        self._track_payment(success)
        self.assertIn("outstanding", failure.text.lower())

        self.assertEqual(self._payable_count(invoice["id"]), 1)
        payable = self._payable(invoice["id"])
        self.assertIsNotNone(payable)
        self.assertGreaterEqual(payable["outstanding"], Decimal("0"))
        self.assertEqual(payable["outstanding"], Decimal("20.00"))
        self.assertEqual(payable["status"], "partial")
        self.assertEqual(self._payment_count(invoice["id"]), 1)
        self.assertEqual(self._completed_sum(invoice["id"]), Decimal("80.00"))

    def test_viewer_cannot_create_payment(self) -> None:
        token, invoice = self._approved_invoice()
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self._pay(viewer, invoice["id"], "10.00")
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIsNone(self._payable(invoice["id"]))

    def test_org_b_cannot_pay_org_a_invoice(self) -> None:
        token_a, invoice_a = self._approved_invoice()
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self._pay(token_b, invoice_a["id"], "10.00")
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertIsNone(self._payable(invoice_a["id"]))

        admin_b = token_b
        invoice_b = self._pending_invoice(admin_b, amount="100.00", gst="0")
        approved_b = self.client.patch(f"{INVOICES_URL}/{invoice_b['id']}/approve", headers=self._auth(admin_b))
        self.assertEqual(approved_b.status_code, 200, approved_b.text)
        paid_b = self._pay(
            admin_b,
            invoice_b["id"],
            "25.00",
            extra={"organizationId": "00000000-0000-0000-0000-000000000001"},
        )
        self.assertEqual(paid_b.status_code, 201, paid_b.text)
        payment_b = self._track_payment(paid_b)
        self.assertEqual(payment_b["organizationId"], str(self.org_b_id))

        listed_b = self.client.get(f"{PAYMENTS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertIn(payment_b["id"], ids_b)

        listed_a = self.client.get(f"{PAYMENTS_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed_a.status_code, 200, listed_a.text)
        self.assertNotIn(payment_b["id"], [item["id"] for item in listed_a.json()["data"]])

    def test_get_payment_by_id_is_tenant_scoped(self) -> None:
        token_a, invoice_a = self._approved_invoice()
        created = self._pay(token_a, invoice_a["id"], "10.00")
        self.assertEqual(created.status_code, 201, created.text)
        payment = self._track_payment(created)

        fetched = self.client.get(f"{PAYMENTS_URL}/{payment['id']}", headers=self._auth(token_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], payment["id"])
        self.assertEqual(fetched.json()["data"]["supplierInvoiceId"], invoice_a["id"])

        missing = self.client.get(f"{PAYMENTS_URL}/{uuid4()}", headers=self._auth(token_a))
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{PAYMENTS_URL}/{payment['id']}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

    def test_list_payables_exposes_table_and_is_tenant_scoped(self) -> None:
        token_a, invoice_a = self._approved_invoice(amount="80.00", gst="0")
        paid = self._pay(token_a, invoice_a["id"], "30.00")
        self.assertEqual(paid.status_code, 201, paid.text)
        self._track_payment(paid)

        listed = self.client.get(f"{PAYABLES_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed.status_code, 200, listed.text)
        row = next((item for item in listed.json()["data"] if item["sourceId"] == invoice_a["id"]), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["sourceType"], "supplier_invoice")
        self.assertEqual(Decimal(str(row["amount"])), Decimal("80.00"))
        self.assertEqual(Decimal(str(row["outstanding"])), Decimal("50.00"))
        self.assertEqual(row["status"], "partial")
        self.assertEqual(row["invoiceNumber"], invoice_a.get("invoiceNumber") or invoice_a.get("invoice_number"))

        viewer = self._login("viewer@demo-business.com", "viewer123")
        viewed = self.client.get(f"{PAYABLES_URL}?page=1&page_size=100", headers=self._auth(viewer))
        self.assertEqual(viewed.status_code, 200, viewed.text)
        self.assertIn(row["id"], [item["id"] for item in viewed.json()["data"]])

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{PAYABLES_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(row["id"], [item["id"] for item in listed_b.json()["data"]])
        self.assertNotIn(invoice_a["id"], [item["sourceId"] for item in listed_b.json()["data"]])


if __name__ == "__main__":
    unittest.main()
