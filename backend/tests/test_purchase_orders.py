"""P2P purchase-order API: approved-PR conversion, RBAC, and tenant isolation."""

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
from app.models.user import User, UserSession
from app.models.vendor import Vendor

VENDORS_URL = "/api/v1/p2p/vendors"
PRS_URL = "/api/v1/p2p/purchase-requests"
POS_URL = "/api/v1/p2p/purchase-orders"
GRNS_URL = "/api/v1/p2p/goods-receipts"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-po-test-"
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


class PurchaseOrderApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_po_ids: list
    created_pr_ids: list
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
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
                name="PO Isolation Org",
                slug=f"iso-po-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-po-admin",
                    email=email,
                    full_name="PO Isolation Admin",
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
            if cls.created_po_ids:
                await session.execute(
                    delete(GoodsReceipt).where(GoodsReceipt.purchase_order_id.in_(cls.created_po_ids))
                )
                await session.execute(delete(PurchaseOrder).where(PurchaseOrder.id.in_(cls.created_po_ids)))
            marked_prs = select(PurchaseRequest.id).where(PurchaseRequest.notes.like(f"{TEST_MARKER}%"))
            await session.execute(delete(PurchaseOrder).where(PurchaseOrder.purchase_request_id.in_(marked_prs)))
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

    def _create_pr(self, token: str, *, vendor_id: str, pr_status: str) -> dict:
        response = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={
                "vendorId": vendor_id,
                "status": pr_status,
                "notes": f"{TEST_MARKER}{pr_status}-{uuid4().hex[:6]}",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.created_pr_ids.append(data["id"])
        return data

    def _pr_status(self, token: str, pr_id: str) -> str:
        listed = self.client.get(f"{PRS_URL}?page=1&page_size=100", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        match = next((item for item in listed.json()["data"] if item["id"] == pr_id), None)
        self.assertIsNotNone(match)
        return match["status"]

    def test_approved_pr_converts_to_po_with_unique_numbers(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_id = self._create_vendor(admin)
        year = date.today().year

        first_pr = self._create_pr(operator, vendor_id=vendor_id, pr_status="approved")
        first = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={
                "purchaseRequestId": first_pr["id"],
                "vendorId": vendor_id,
                "totalAmount": "24500.00",
                "status": "draft",
                "poNumber": "PO-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        po_a = first.json()["data"]
        self.created_po_ids.append(po_a["id"])
        number_a = po_a.get("poNumber") or po_a.get("po_number")
        self.assertRegex(number_a, rf"^PO-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, "PO-SHOULD-BE-IGNORED")
        self.assertEqual(po_a["purchaseRequestId"], first_pr["id"])
        self.assertEqual(self._pr_status(operator, first_pr["id"]), "converted")
        self.assertEqual(Decimal(str(po_a.get("totalAmount") or po_a.get("total_amount"))), Decimal("24500.00"))

        second_pr = self._create_pr(operator, vendor_id=vendor_id, pr_status="approved")
        second = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"purchaseRequestId": second_pr["id"], "vendorId": vendor_id, "totalAmount": "12800.00"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        po_b = second.json()["data"]
        self.created_po_ids.append(po_b["id"])
        number_b = po_b.get("poNumber") or po_b.get("po_number")
        self.assertRegex(number_b, rf"^PO-{year}-\d{{3,}}$")
        self.assertNotEqual(number_a, number_b)
        self.assertEqual(self._pr_status(operator, second_pr["id"]), "converted")

        listed = self.client.get(f"{POS_URL}?page=1&page_size=20", headers=self._auth(operator))
        self.assertEqual(listed.status_code, 200, listed.text)
        ids = [item["id"] for item in listed.json()["data"]]
        self.assertIn(po_a["id"], ids)
        self.assertIn(po_b["id"], ids)

    def test_rejects_draft_and_converted_purchase_requests(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_id = self._create_vendor(admin)

        draft = self._create_pr(operator, vendor_id=vendor_id, pr_status="draft")
        draft_po = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"purchaseRequestId": draft["id"], "vendorId": vendor_id},
        )
        self.assertEqual(draft_po.status_code, 400, draft_po.text)
        self.assertEqual(self._pr_status(operator, draft["id"]), "draft")

        approved = self._create_pr(operator, vendor_id=vendor_id, pr_status="approved")
        created = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"purchaseRequestId": approved["id"], "vendorId": vendor_id},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.created_po_ids.append(created.json()["data"]["id"])
        self.assertEqual(self._pr_status(operator, approved["id"]), "converted")

        again = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"purchaseRequestId": approved["id"], "vendorId": vendor_id},
        )
        self.assertEqual(again.status_code, 400, again.text)

    def test_creates_purchase_order_without_a_purchase_request(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_id = self._create_vendor(admin)
        year = date.today().year

        created = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_id, "totalAmount": "1500.00", "status": "issued", "purchaseRequestId": ""},
        )
        self.assertEqual(created.status_code, 201, created.text)
        po = created.json()["data"]
        self.created_po_ids.append(po["id"])
        self.assertIsNone(po.get("purchaseRequestId"))
        self.assertEqual(po.get("purchaseRequestNumber") or "", "")
        self.assertEqual(po["vendorId"], vendor_id)
        self.assertRegex(po.get("poNumber") or po.get("po_number"), rf"^PO-{year}-\d{{3,}}$")
        self.assertEqual(Decimal(str(po.get("totalAmount") or po.get("total_amount"))), Decimal("1500.00"))

        missing_vendor = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"totalAmount": "10.00"},
        )
        self.assertEqual(missing_vendor.status_code, 400, missing_vendor.text)

    def test_rejects_purchase_request_from_another_org(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        vendor_a = self._create_vendor(admin_a)
        pr_a = self._create_pr(admin_a, vendor_id=vendor_a, pr_status="approved")

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        vendor_b = self._create_vendor(token_b)
        stolen = self.client.post(
            POS_URL,
            headers=self._auth(token_b),
            json={"purchaseRequestId": pr_a["id"], "vendorId": vendor_b},
        )
        self.assertEqual(stolen.status_code, 404, stolen.text)
        self.assertEqual(self._pr_status(admin_a, pr_a["id"]), "approved")

    def test_viewer_cannot_create_purchase_order(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        vendor_id = self._create_vendor(admin)
        pr = self._create_pr(admin, vendor_id=vendor_id, pr_status="approved")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            POS_URL,
            headers=self._auth(viewer),
            json={"purchaseRequestId": pr["id"], "vendorId": vendor_id},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self._pr_status(admin, pr["id"]), "approved")

    def test_purchase_order_created_in_org_a_is_invisible_to_org_b(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        vendor_a = self._create_vendor(admin_a)
        pr_a = self._create_pr(admin_a, vendor_id=vendor_a, pr_status="approved")
        create = self.client.post(
            POS_URL,
            headers=self._auth(admin_a),
            json={"purchaseRequestId": pr_a["id"], "vendorId": vendor_a, "totalAmount": "10.00"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        po_id = create.json()["data"]["id"]
        self.created_po_ids.append(po_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{POS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(po_id, [item["id"] for item in listed_b.json()["data"]])

        vendor_b = self._create_vendor(token_b)
        pr_b = self._create_pr(token_b, vendor_id=vendor_b, pr_status="approved")
        spoof = self.client.post(
            POS_URL,
            headers=self._auth(token_b),
            json={
                "purchaseRequestId": pr_b["id"],
                "vendorId": vendor_b,
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_po_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))

    def test_get_purchase_order_by_id_is_tenant_scoped(self) -> None:
        admin_a = self._login("admin@demo-business.com", "admin123")
        vendor_a = self._create_vendor(admin_a)
        created = self.client.post(
            POS_URL,
            headers=self._auth(admin_a),
            json={"vendorId": vendor_a, "totalAmount": "10.00", "status": "issued"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        po_id = created.json()["data"]["id"]
        self.created_po_ids.append(po_id)

        fetched = self.client.get(f"{POS_URL}/{po_id}", headers=self._auth(admin_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], po_id)
        self.assertEqual(fetched.json()["data"]["vendorId"], vendor_a)

        missing = self.client.get(f"{POS_URL}/{uuid4()}", headers=self._auth(admin_a))
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{POS_URL}/{po_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

    def test_list_filters_by_vendor_status_and_search(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        vendor_a = self._create_vendor(admin)
        vendor_b = self._create_vendor(admin)
        draft_a = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_a, "totalAmount": "10.00", "status": "draft"},
        )
        issued_a = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_a, "totalAmount": "20.00", "status": "issued"},
        )
        draft_b = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_b, "totalAmount": "30.00", "status": "draft"},
        )
        self.assertEqual(draft_a.status_code, 201, draft_a.text)
        self.assertEqual(issued_a.status_code, 201, issued_a.text)
        self.assertEqual(draft_b.status_code, 201, draft_b.text)
        id_draft_a = draft_a.json()["data"]["id"]
        id_issued_a = issued_a.json()["data"]["id"]
        id_draft_b = draft_b.json()["data"]["id"]
        self.created_po_ids.extend([id_draft_a, id_issued_a, id_draft_b])
        number_a = draft_a.json()["data"].get("poNumber") or draft_a.json()["data"].get("po_number")

        filtered = self.client.get(
            f"{POS_URL}?page=1&page_size=20&vendor_id={vendor_a}&status=draft",
            headers=self._auth(operator),
        )
        self.assertEqual(filtered.status_code, 200, filtered.text)
        ids = [item["id"] for item in filtered.json()["data"]]
        self.assertEqual(ids, [id_draft_a])
        self.assertEqual(filtered.json()["meta"].get("total"), 1)
        self.assertNotIn(id_issued_a, ids)
        self.assertNotIn(id_draft_b, ids)

        by_number = self.client.get(
            f"{POS_URL}?page=1&page_size=20&search={number_a}",
            headers=self._auth(operator),
        )
        self.assertEqual(by_number.status_code, 200, by_number.text)
        self.assertEqual([item["id"] for item in by_number.json()["data"]], [id_draft_a])

    def test_operator_can_issue_draft_po_then_record_grn(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        viewer = self._login("viewer@demo-business.com", "viewer123")
        vendor_id = self._create_vendor(admin)

        created = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_id, "totalAmount": "2200.00", "status": "draft"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        po_id = created.json()["data"]["id"]
        self.created_po_ids.append(po_id)

        blocked_grn = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": po_id, "status": "received"},
        )
        self.assertEqual(blocked_grn.status_code, 400, blocked_grn.text)

        viewer_issue = self.client.patch(f"{POS_URL}/{po_id}/issue", headers=self._auth(viewer))
        self.assertEqual(viewer_issue.status_code, 403, viewer_issue.text)

        issued = self.client.patch(f"{POS_URL}/{po_id}/issue", headers=self._auth(operator))
        self.assertEqual(issued.status_code, 200, issued.text)
        self.assertEqual(issued.json()["data"]["status"], "issued")

        again = self.client.patch(f"{POS_URL}/{po_id}/issue", headers=self._auth(operator))
        self.assertEqual(again.status_code, 400, again.text)

        already_issued = self.client.post(
            POS_URL,
            headers=self._auth(operator),
            json={"vendorId": vendor_id, "totalAmount": "10.00", "status": "issued"},
        )
        self.assertEqual(already_issued.status_code, 201, already_issued.text)
        issued_id = already_issued.json()["data"]["id"]
        self.created_po_ids.append(issued_id)
        wrong_status = self.client.patch(f"{POS_URL}/{issued_id}/issue", headers=self._auth(operator))
        self.assertEqual(wrong_status.status_code, 400, wrong_status.text)

        grn = self.client.post(
            GRNS_URL,
            headers=self._auth(operator),
            json={"purchaseOrderId": po_id, "status": "received"},
        )
        self.assertEqual(grn.status_code, 201, grn.text)
        self.assertEqual(grn.json()["data"]["purchaseOrderId"], po_id)

        missing = self.client.patch(
            f"{POS_URL}/00000000-0000-0000-0000-000000000099/issue",
            headers=self._auth(operator),
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.patch(f"{POS_URL}/{po_id}/issue", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)


if __name__ == "__main__":
    unittest.main()
