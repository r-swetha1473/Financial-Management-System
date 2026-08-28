"""P2P supplier-invoice API: GRN billing, RBAC, and tenant isolation."""

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
TEST_MARKER = "p2p-si-test-"
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


class SupplierInvoiceApiTests(unittest.TestCase):
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
                name="SI Isolation Org",
                slug=f"iso-si-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-si-admin",
                    email=email,
                    full_name="SI Isolation Admin",
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
            if cls.created_invoice_ids:
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

    def test_received_grn_creates_invoice_with_pending_defaults_and_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        year = date.today().year
        vendor_id, first_grn = self._received_grn(operator, admin)

        first = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={
                "goodsReceiptId": first_grn["id"],
                "vendorId": vendor_id,
                "amount": "24500.00",
                "gstAmount": "4410.00",
                "status": "paid",
                "approvalStatus": "approved",
                "invoiceNumber": "SI-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        invoice_a = first.json()["data"]
        self.created_invoice_ids.append(invoice_a["id"])
        number_a = invoice_a.get("invoiceNumber") or invoice_a.get("invoice_number")
        self.assertRegex(number_a, rf"^SI-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, "SI-SHOULD-BE-IGNORED")
        self.assertEqual(invoice_a["status"], "pending")
        self.assertEqual(invoice_a.get("approvalStatus") or invoice_a.get("approval_status"), "pending")
        self.assertEqual(invoice_a["goodsReceiptId"], first_grn["id"])
        self.assertEqual(Decimal(str(invoice_a["amount"])), Decimal("24500.00"))
        self.assertEqual(Decimal(str(invoice_a.get("gstAmount") or invoice_a.get("gst_amount"))), Decimal("4410.00"))

        _, second_grn = self._received_grn(operator, admin, vendor_id=vendor_id)
        second = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"goodsReceiptId": second_grn["id"], "amount": "100.00", "gstAmount": "18.00"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        invoice_b = second.json()["data"]
        self.created_invoice_ids.append(invoice_b["id"])
        number_b = invoice_b.get("invoiceNumber") or invoice_b.get("invoice_number")
        self.assertRegex(number_b, rf"^SI-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, number_b)

        listed = self.client.get(f"{INVOICES_URL}?page=1&page_size=20", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(invoice_a["id"], ids)
        self.assertIn(invoice_b["id"], ids)

    def test_rejects_second_invoice_against_same_grn(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_id, grn = self._received_grn(operator, admin)
        created = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"goodsReceiptId": grn["id"], "vendorId": vendor_id, "amount": "10.00"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.created_invoice_ids.append(created.json()["data"]["id"])

        again = self.client.post(
            INVOICES_URL,
            headers=self._auth(operator),
            json={"goodsReceiptId": grn["id"], "vendorId": vendor_id, "amount": "5.00"},
        )
        self.assertEqual(again.status_code, 400, again.text)

    def test_rejects_goods_receipt_from_another_org(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, grn_a = self._received_grn(admin_a)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.post(
            INVOICES_URL,
            headers=self._auth(token_b),
            json={"goodsReceiptId": grn_a["id"], "amount": "10.00"},
        )
        self.assertEqual(stolen.status_code, 404, stolen.text)

    def test_viewer_cannot_create_supplier_invoice(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        _, grn = self._received_grn(admin)
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            INVOICES_URL,
            headers=self._auth(viewer),
            json={"goodsReceiptId": grn["id"], "amount": "10.00"},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_supplier_invoice_created_in_org_a_is_invisible_to_org_b(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, grn_a = self._received_grn(admin_a)
        create = self.client.post(
            INVOICES_URL,
            headers=self._auth(admin_a),
            json={"goodsReceiptId": grn_a["id"], "amount": "10.00"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        invoice_id = create.json()["data"]["id"]
        self.created_invoice_ids.append(invoice_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{INVOICES_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(invoice_id, [item["id"] for item in listed_b.json()["data"]])

        _, grn_b = self._received_grn(token_b)
        spoof = self.client.post(
            INVOICES_URL,
            headers=self._auth(token_b),
            json={
                "goodsReceiptId": grn_b["id"],
                "amount": "10.00",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_invoice_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))

    def test_get_supplier_invoice_by_id_is_tenant_scoped(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, grn_a = self._received_grn(admin_a)
        create = self.client.post(
            INVOICES_URL,
            headers=self._auth(admin_a),
            json={"goodsReceiptId": grn_a["id"], "amount": "10.00"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        invoice_id = create.json()["data"]["id"]
        self.created_invoice_ids.append(invoice_id)

        fetched = self.client.get(f"{INVOICES_URL}/{invoice_id}", headers=self._auth(admin_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], invoice_id)
        self.assertEqual(fetched.json()["data"]["goodsReceiptId"], grn_a["id"])

        missing = self.client.get(f"{INVOICES_URL}/{uuid4()}", headers=self._auth(admin_a))
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{INVOICES_URL}/{invoice_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)


if __name__ == "__main__":
    unittest.main()
