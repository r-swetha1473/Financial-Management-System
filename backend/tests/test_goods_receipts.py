"""P2P goods-receipt API: issued-PO receiving, RBAC, and tenant isolation."""

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
from app.models.goods_receipt import GoodsReceipt
from app.models.organization import Organization
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_request import PurchaseRequest
from app.models.user import User, UserSession
from app.models.vendor import Vendor

VENDORS_URL = "/api/v1/p2p/vendors"
PRS_URL = "/api/v1/p2p/purchase-requests"
POS_URL = "/api/v1/p2p/purchase-orders"
GRNS_URL = "/api/v1/p2p/goods-receipts"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-grn-test-"
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


class GoodsReceiptApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_grn_ids: list
    created_po_ids: list
    created_pr_ids: list
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
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
                name="GRN Isolation Org",
                slug=f"iso-grn-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-grn-admin",
                    email=email,
                    full_name="GRN Isolation Admin",
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
            if cls.created_grn_ids:
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

    def _create_pr(self, token: str, *, vendor_id: str) -> dict:
        response = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={
                "vendorId": vendor_id,
                "status": "approved",
                "notes": f"{TEST_MARKER}{uuid4().hex[:6]}",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_pr_ids.append(data["id"])
        return data

    def _create_po(self, token: str, *, vendor_id: str, pr_id: str, po_status: str) -> dict:
        response = self.client.post(
            POS_URL,
            headers=self._auth(token),
            json={
                "purchaseRequestId": pr_id,
                "vendorId": vendor_id,
                "status": po_status,
                "totalAmount": "100.00",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_po_ids.append(data["id"])
        return data

    def _issued_po(self, token: str, admin: str | None = None) -> tuple[str, dict]:
        vendor_token = admin or token
        vendor_id = self._create_vendor(vendor_token)
        pr = self._create_pr(token, vendor_id=vendor_id)
        po = self._create_po(token, vendor_id=vendor_id, pr_id=pr["id"], po_status="issued")
        return vendor_id, po

    def _po_status(self, token: str, po_id: str) -> str:
        listed = self.client.get(f"{POS_URL}?page=1&page_size=100", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        match = next((item for item in listed.json()["data"] if item["id"] == po_id), None)
        self.assertIsNotNone(match)
        return match["status"]

    def test_issued_po_converts_to_grn_with_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        year = date.today().year
        vendor_id, first_po = self._issued_po(operator, admin)

        first = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={
                "purchaseOrderId": first_po["id"],
                "status": "received",
                "grnNumber": "GRN-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        grn_a = first.json()["data"]
        self.created_grn_ids.append(grn_a["id"])
        number_a = grn_a.get("grnNumber") or grn_a.get("grn_number")
        self.assertRegex(number_a, rf"^GRN-{year}-\d{{3}}$")
        self.assertNotEqual(number_a, "GRN-SHOULD-BE-IGNORED")
        self.assertEqual(grn_a["purchaseOrderId"], first_po["id"])
        self.assertEqual(self._po_status(operator, first_po["id"]), "received")

        pr_b = self._create_pr(operator, vendor_id=vendor_id)
        second_po = self._create_po(operator, vendor_id=vendor_id, pr_id=pr_b["id"], po_status="issued")
        second = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": second_po["id"]},
        )
        self.assertEqual(second.status_code, 201, second.text)
        grn_b = second.json()["data"]
        self.created_grn_ids.append(grn_b["id"])
        number_b = grn_b.get("grnNumber") or grn_b.get("grn_number")
        self.assertRegex(number_b, rf"^GRN-{year}-\d{{3}}$")
        self.assertNotEqual(number_a, number_b)
        self.assertEqual(self._po_status(operator, second_po["id"]), "received")

        listed = self.client.get(f"{GRNS_URL}?page=1&page_size=20", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(grn_a["id"], ids)
        self.assertIn(grn_b["id"], ids)

    def test_rejects_draft_and_already_received_purchase_orders(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_id = self._create_vendor(admin)
        draft_pr = self._create_pr(operator, vendor_id=vendor_id)
        draft_po = self._create_po(operator, vendor_id=vendor_id, pr_id=draft_pr["id"], po_status="draft")
        draft_grn = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": draft_po["id"]},
        )
        self.assertEqual(draft_grn.status_code, 400, draft_grn.text)
        self.assertEqual(self._po_status(operator, draft_po["id"]), "draft")

        issued_pr = self._create_pr(operator, vendor_id=vendor_id)
        issued_po = self._create_po(operator, vendor_id=vendor_id, pr_id=issued_pr["id"], po_status="issued")
        created = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": issued_po["id"]},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.created_grn_ids.append(created.json()["data"]["id"])
        self.assertEqual(self._po_status(operator, issued_po["id"]), "received")

        again = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": issued_po["id"]},
        )
        self.assertEqual(again.status_code, 400, again.text)

    def test_rejects_purchase_order_from_another_org(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, po_a = self._issued_po(admin_a)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.post(
            GRNS_URL,
            headers=self._auth(token_b),
            json={"purchaseOrderId": po_a["id"]},
        )
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertEqual(self._po_status(admin_a, po_a["id"]), "issued")

    def test_viewer_cannot_create_goods_receipt(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        _, po = self._issued_po(admin)
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            GRNS_URL,
            headers=self._auth(viewer),
            json={"purchaseOrderId": po["id"]},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self._po_status(admin, po["id"]), "issued")

    def test_goods_receipt_created_in_org_a_is_invisible_to_org_b(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, po_a = self._issued_po(admin_a)
        create = self.client.post(
            GRNS_URL,
            headers=self._auth(admin_a),
            json={"purchaseOrderId": po_a["id"]},
        )
        self.assertEqual(create.status_code, 201, create.text)
        grn_id = create.json()["data"]["id"]
        self.created_grn_ids.append(grn_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{GRNS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(grn_id, [item["id"] for item in listed_b.json()["data"]])

        _, po_b = self._issued_po(token_b)
        spoof = self.client.post(
            GRNS_URL,
            headers=self._auth(token_b),
            json={
                "purchaseOrderId": po_b["id"],
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_grn_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))

    def test_get_goods_receipt_by_id_is_tenant_scoped(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        _, po_a = self._issued_po(admin_a)
        create = self.client.post(
            GRNS_URL,
            headers=self._auth(admin_a),
            json={"purchaseOrderId": po_a["id"]},
        )
        self.assertEqual(create.status_code, 201, create.text)
        grn_id = create.json()["data"]["id"]
        self.created_grn_ids.append(grn_id)

        fetched = self.client.get(f"{GRNS_URL}/{grn_id}", headers=self._auth(admin_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], grn_id)
        self.assertEqual(fetched.json()["data"]["purchaseOrderId"], po_a["id"])

        missing = self.client.get(f"{GRNS_URL}/{uuid4()}", headers=self._auth(admin_a))
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{GRNS_URL}/{grn_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)


if __name__ == "__main__":
    unittest.main()
