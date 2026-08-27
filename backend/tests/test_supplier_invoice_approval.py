"""P2P supplier-invoice approve/reject: maker-checker, lock, audit, tenant isolation."""

from __future__ import annotations

import asyncio
import unittest
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
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-si-appr-"
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


class SupplierInvoiceApprovalApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_invoice_ids: list
    created_grn_ids: list
    created_po_ids: list
    created_pr_ids: list
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
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
                name="SI Approval Isolation Org",
                slug=f"iso-si-appr-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-si-appr-admin",
                    email=email,
                    full_name="SI Approval Isolation Admin",
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
            if cls.created_invoice_ids:
                await session.execute(
                    delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_invoice_ids))
                )
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
            json={"purchaseRequestId": pr_id, "vendorId": vendor_id, "status": "issued", "totalAmount": "24500.00"},
        )
        self.assertEqual(po.status_code, 201, po.text)
        po_id = po.json()["data"]["id"]
        self.created_po_ids.append(po_id)
        grn = self.client.post(GRNS_URL, headers=self._auth(token), json={"purchaseOrderId": po_id})
        self.assertEqual(grn.status_code, 201, grn.text)
        data = grn.json()["data"]
        self.created_grn_ids.append(data["id"])
        return vendor_id, data

    def _pending_invoice(self, creator: str, admin: str | None = None) -> dict:
        vendor_id, grn = self._received_grn(creator, admin)
        created = self.client.post(
            INVOICES_URL,
            headers=self._auth(creator),
            json={"goodsReceiptId": grn["id"], "vendorId": vendor_id, "amount": "24500.00", "gstAmount": "4410.00"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        invoice = created.json()["data"]
        self.created_invoice_ids.append(invoice["id"])
        self.assertEqual(_approval(invoice), "pending")
        return invoice

    def _audit_count(self, invoice_id: str, action: str) -> int:
        async def work(session: AsyncSession):
            return await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.entity_id == invoice_id, AuditLog.action == action)
            )

        return int(_run(_with_own_session(work)) or 0)

    def _payable_count(self, invoice_id: str) -> int:
        async def work(session: AsyncSession):
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM payables "
                    "WHERE source_type = 'supplier_invoice' AND source_id = CAST(:sid AS uuid)"
                ),
                {"sid": invoice_id},
            )
            return result.scalar()

        return int(_run(_with_own_session(work)) or 0)

    def _grn_status(self, grn_id: str) -> str:
        async def work(session: AsyncSession):
            return await session.scalar(select(GoodsReceipt.status).where(GoodsReceipt.id == grn_id))

        return str(_run(_with_own_session(work)))

    def test_finance_approves_pending_invoice(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        finance = self._login("finance@demo-business.com", "finance123")
        invoice = self._pending_invoice(operator, admin)
        grn_id = invoice.get("goodsReceiptId") or invoice.get("goods_receipt_id")
        grn_before = self._grn_status(grn_id)

        response = self.client.patch(
            f"{INVOICES_URL}/{invoice['id']}/approve",
            headers=self._auth(finance),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(_approval(data), "approved")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(self._payable_count(invoice["id"]), 0)
        self.assertEqual(self._grn_status(grn_id), grn_before)
        self.assertEqual(self._audit_count(invoice["id"], "approve"), 1)

    def test_manager_rejects_pending_invoice(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        manager = self._login("manager@demo-business.com", "manager123")
        invoice = self._pending_invoice(operator, admin)

        response = self.client.patch(
            f"{INVOICES_URL}/{invoice['id']}/reject",
            headers=self._auth(manager),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(_approval(data), "rejected")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(self._payable_count(invoice["id"]), 0)
        self.assertEqual(self._audit_count(invoice["id"], "reject"), 1)

    def test_rejects_if_already_approved_or_rejected(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        finance = self._login("finance@demo-business.com", "finance123")
        invoice = self._pending_invoice(operator, admin)

        first = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(finance))
        self.assertEqual(first.status_code, 200, first.text)

        reapprove = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(finance))
        self.assertEqual(reapprove.status_code, 400, reapprove.text)
        self.assertIn("already been approved", reapprove.text)

        unreject = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/reject", headers=self._auth(finance))
        self.assertEqual(unreject.status_code, 400, unreject.text)

        other = self._pending_invoice(operator, admin)
        rejected = self.client.patch(f"{INVOICES_URL}/{other['id']}/reject", headers=self._auth(admin))
        self.assertEqual(rejected.status_code, 200, rejected.text)
        again = self.client.patch(f"{INVOICES_URL}/{other['id']}/approve", headers=self._auth(finance))
        self.assertEqual(again.status_code, 400, again.text)
        self.assertIn("already been rejected", again.text)

    def test_operator_cannot_approve_or_reject(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        invoice = self._pending_invoice(operator, admin)

        approve = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(operator))
        self.assertEqual(approve.status_code, 403, approve.text)

        reject = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/reject", headers=self._auth(operator))
        self.assertEqual(reject.status_code, 403, reject.text)
        self.assertEqual(_approval(invoice), "pending")

        listed = self.client.get(f"{INVOICES_URL}?page=1&page_size=100", headers=self._auth(operator))
        match = next(item for item in listed.json()["data"] if item["id"] == invoice["id"])
        self.assertEqual(_approval(match), "pending")

    def test_org_b_cannot_approve_org_a_invoice(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        invoice = self._pending_invoice(admin_a)
        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)

        stolen = self.client.patch(f"{INVOICES_URL}/{invoice['id']}/approve", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        listed = self.client.get(f"{INVOICES_URL}?page=1&page_size=100", headers=self._auth(admin_a))
        match = next(item for item in listed.json()["data"] if item["id"] == invoice["id"])
        self.assertEqual(_approval(match), "pending")

        _, grn_b = self._received_grn(token_b)
        create_b = self.client.post(
            INVOICES_URL,
            headers=self._auth(token_b),
            json={
                "goodsReceiptId": grn_b["id"],
                "amount": "10.00",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(create_b.status_code, 201, create_b.text)
        invoice_b = create_b.json()["data"]
        self.created_invoice_ids.append(invoice_b["id"])
        self.assertEqual(invoice_b["organizationId"], str(self.org_b_id))

        approve_b = self.client.patch(f"{INVOICES_URL}/{invoice_b['id']}/approve", headers=self._auth(token_b))
        self.assertEqual(approve_b.status_code, 200, approve_b.text)
        self.assertEqual(_approval(approve_b.json()["data"]), "approved")
        self.assertEqual(approve_b.json()["data"]["organizationId"], str(self.org_b_id))


if __name__ == "__main__":
    unittest.main()
