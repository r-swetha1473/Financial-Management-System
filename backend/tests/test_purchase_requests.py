"""P2P purchase-request API: sequence numbers, RBAC, and tenant isolation."""

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
from tests.audit_teardown import allow_audit_delete_for_tests
from app.main import app
from app.models.organization import Organization
from app.models.purchase_request import PurchaseRequest
from app.models.audit_log import AuditLog
from app.models.user import User, UserSession
from app.models.vendor import Vendor

PRS_URL = "/api/v1/p2p/purchase-requests"
VENDORS_URL = "/api/v1/p2p/vendors"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-pr-test-"
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


class PurchaseRequestApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_ids: list
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_ids = []
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
                name="PR Isolation Org",
                slug=f"iso-pr-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-pr-admin",
                    email=email,
                    full_name="PR Isolation Admin",
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
            if cls.created_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_ids)))
                await session.execute(delete(PurchaseRequest).where(PurchaseRequest.id.in_(cls.created_ids)))
            marked = select(PurchaseRequest.id).where(PurchaseRequest.notes.like(f"{TEST_MARKER}%"))
            await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(marked)))
            await session.execute(delete(PurchaseRequest).where(PurchaseRequest.notes.like(f"{TEST_MARKER}%")))
            if cls.created_vendor_ids:
                await session.execute(delete(Vendor).where(Vendor.id.in_(cls.created_vendor_ids)))
            await session.execute(delete(Vendor).where(Vendor.name.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
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

    def _assert_request_number(self, value: str, year: int | None = None) -> None:
        year = year or date.today().year
        self.assertRegex(value, rf"^PR-{year}-\d{{3,}}$")

    def test_operator_create_and_list_assigns_unique_sequence_numbers(self) -> None:
        token = self._login("operator@demo-business.com", "operator123")
        year = date.today().year
        first = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={
                "notes": f"{TEST_MARKER}one",
                "status": "draft",
                "requestNumber": "PR-SHOULD-BE-IGNORED",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(first.status_code, 201, first.text)
        a = first.json()["data"]
        self.created_ids.append(a["id"])
        number_a = a.get("requestNumber") or a.get("request_number")
        self._assert_request_number(number_a, year)
        self.assertNotEqual(number_a, "PR-SHOULD-BE-IGNORED")
        self.assertEqual(a["organizationId"], "00000000-0000-0000-0000-000000000001")
        self.assertEqual(a.get("requestedByName") or a.get("requested_by_name"), "Records Operator")

        second = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"notes": f"{TEST_MARKER}two", "status": "submitted"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        b = second.json()["data"]
        self.created_ids.append(b["id"])
        number_b = b.get("requestNumber") or b.get("request_number")
        self._assert_request_number(number_b, year)
        self.assertNotEqual(number_a, number_b)

        listed = self.client.get(f"{PRS_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        ids = [item["id"] for item in body["data"]]
        self.assertIn(a["id"], ids)
        self.assertIn(b["id"], ids)
        meta = body["meta"]
        self.assertGreaterEqual(meta.get("total") or 0, 2)
        self.assertEqual(meta.get("page"), 1)

        fetched = self.client.get(f"{PRS_URL}/{a['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], a["id"])

        missing = self.client.get(
            f"{PRS_URL}/00000000-0000-0000-0000-000000000099",
            headers=self._auth(token),
        )
        self.assertEqual(missing.status_code, 404, missing.text)

    def test_viewer_cannot_create_purchase_request(self) -> None:
        token = self._login("viewer@demo-business.com", "viewer123")
        response = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"notes": f"{TEST_MARKER}blocked"},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_purchase_request_created_in_org_a_is_invisible_to_org_b(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        create = self.client.post(
            PRS_URL,
            headers=self._auth(token_a),
            json={"notes": f"{TEST_MARKER}org-a"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        pr_id = create.json()["data"]["id"]
        self.created_ids.append(pr_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{PRS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(pr_id, ids_b)

        stolen = self.client.get(f"{PRS_URL}/{pr_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        spoof = self.client.post(
            PRS_URL,
            headers=self._auth(token_b),
            json={
                "notes": f"{TEST_MARKER}spoof",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))
        self._assert_request_number(spoofed.get("requestNumber") or spoofed.get("request_number"))

    def test_put_on_purchase_request_is_not_allowed(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        created = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"notes": f"{TEST_MARKER}no-put", "status": "draft"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        pr_id = created.json()["data"]["id"]
        self.created_ids.append(pr_id)

        updated = self.client.put(
            f"{PRS_URL}/{pr_id}",
            headers=self._auth(token),
            json={"status": "approved", "notes": "should not update"},
        )
        self.assertEqual(updated.status_code, 501, updated.text)
        self.assertIn("not supported", updated.text.lower())
        fetched = self.client.get(f"{PRS_URL}/{pr_id}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["status"], "draft")

    def test_admin_can_approve_draft_and_operator_cannot(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        operator = self._login("operator@demo-business.com", "operator123")
        created = self.client.post(
            PRS_URL,
            headers=self._auth(operator),
            json={"notes": f"{TEST_MARKER}approve-me", "status": "draft"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        pr_id = created.json()["data"]["id"]
        self.created_ids.append(pr_id)

        blocked = self.client.patch(f"{PRS_URL}/{pr_id}/approve", headers=self._auth(operator))
        self.assertEqual(blocked.status_code, 403, blocked.text)

        approved = self.client.patch(f"{PRS_URL}/{pr_id}/approve", headers=self._auth(admin))
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["data"]["status"], "approved")

        again = self.client.patch(f"{PRS_URL}/{pr_id}/approve", headers=self._auth(admin))
        self.assertEqual(again.status_code, 400, again.text)

        other = self.client.post(
            PRS_URL,
            headers=self._auth(operator),
            json={"notes": f"{TEST_MARKER}reject-me", "status": "submitted"},
        )
        self.assertEqual(other.status_code, 201, other.text)
        other_id = other.json()["data"]["id"]
        self.created_ids.append(other_id)
        rejected = self.client.patch(f"{PRS_URL}/{other_id}/reject", headers=self._auth(admin))
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["data"]["status"], "rejected")

        missing = self.client.patch(
            f"{PRS_URL}/00000000-0000-0000-0000-000000000099/approve",
            headers=self._auth(admin),
        )
        self.assertEqual(missing.status_code, 404, missing.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.patch(f"{PRS_URL}/{pr_id}/approve", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

    def _create_vendor(self, token: str, name: str | None = None) -> str:
        response = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={"name": name or f"{TEST_MARKER}{uuid4().hex[:8]}", "status": "active"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        vendor_id = response.json()["data"]["id"]
        self.created_vendor_ids.append(vendor_id)
        return vendor_id

    def test_list_filters_by_search_vendor_and_status(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        vendor_a = self._create_vendor(admin, f"{TEST_MARKER}Alpha Supplies")
        vendor_b = self._create_vendor(admin, f"{TEST_MARKER}Beta Traders")
        token = self._login("operator@demo-business.com", "operator123")

        draft_a = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"vendorId": vendor_a, "status": "draft", "notes": f"{TEST_MARKER}unique-widget-note"},
        )
        submitted_a = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"vendorId": vendor_a, "status": "submitted", "notes": f"{TEST_MARKER}other"},
        )
        draft_b = self.client.post(
            PRS_URL,
            headers=self._auth(token),
            json={"vendorId": vendor_b, "status": "draft", "notes": f"{TEST_MARKER}other"},
        )
        self.assertEqual(draft_a.status_code, 201, draft_a.text)
        self.assertEqual(submitted_a.status_code, 201, submitted_a.text)
        self.assertEqual(draft_b.status_code, 201, draft_b.text)
        id_draft_a = draft_a.json()["data"]["id"]
        id_submitted_a = submitted_a.json()["data"]["id"]
        id_draft_b = draft_b.json()["data"]["id"]
        self.created_ids.extend([id_draft_a, id_submitted_a, id_draft_b])
        number_a = draft_a.json()["data"].get("requestNumber") or draft_a.json()["data"].get("request_number")

        by_vendor_status = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&vendor_id={vendor_a}&status=draft",
            headers=self._auth(token),
        )
        self.assertEqual(by_vendor_status.status_code, 200, by_vendor_status.text)
        vendor_ids = [item["id"] for item in by_vendor_status.json()["data"]]
        self.assertEqual(vendor_ids, [id_draft_a])
        self.assertEqual(by_vendor_status.json()["meta"].get("total"), 1)

        by_notes = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&search=unique-widget-note",
            headers=self._auth(token),
        )
        self.assertEqual(by_notes.status_code, 200, by_notes.text)
        note_ids = [item["id"] for item in by_notes.json()["data"]]
        self.assertEqual(note_ids, [id_draft_a])

        by_vendor_name = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&search=Alpha Supplies",
            headers=self._auth(token),
        )
        self.assertEqual(by_vendor_name.status_code, 200, by_vendor_name.text)
        name_ids = [item["id"] for item in by_vendor_name.json()["data"]]
        self.assertIn(id_draft_a, name_ids)
        self.assertIn(id_submitted_a, name_ids)
        self.assertNotIn(id_draft_b, name_ids)

        by_number = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&search={number_a}",
            headers=self._auth(token),
        )
        self.assertEqual(by_number.status_code, 200, by_number.text)
        number_ids = [item["id"] for item in by_number.json()["data"]]
        self.assertEqual(number_ids, [id_draft_a])

    def test_list_filters_stay_tenant_scoped(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        vendor_a = self._create_vendor(token_a, f"{TEST_MARKER}OrgA Vendor")
        create_a = self.client.post(
            PRS_URL,
            headers=self._auth(token_a),
            json={"vendorId": vendor_a, "status": "draft", "notes": f"{TEST_MARKER}org-a-filter"},
        )
        self.assertEqual(create_a.status_code, 201, create_a.text)
        pr_a = create_a.json()["data"]["id"]
        self.created_ids.append(pr_a)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        vendor_b = self._create_vendor(token_b, f"{TEST_MARKER}OrgB Vendor")
        create_b = self.client.post(
            PRS_URL,
            headers=self._auth(token_b),
            json={"vendorId": vendor_b, "status": "draft", "notes": f"{TEST_MARKER}org-b-filter"},
        )
        self.assertEqual(create_b.status_code, 201, create_b.text)
        pr_b = create_b.json()["data"]["id"]
        self.created_ids.append(pr_b)

        stolen = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&vendor_id={vendor_a}&status=draft",
            headers=self._auth(token_b),
        )
        self.assertEqual(stolen.status_code, 200, stolen.text)
        stolen_ids = [item["id"] for item in stolen.json()["data"]]
        self.assertNotIn(pr_a, stolen_ids)

        own = self.client.get(
            f"{PRS_URL}?page=1&page_size=20&vendor_id={vendor_b}&status=draft",
            headers=self._auth(token_b),
        )
        self.assertEqual(own.status_code, 200, own.text)
        own_ids = [item["id"] for item in own.json()["data"]]
        self.assertEqual(own_ids, [pr_b])
        self.assertNotIn(pr_a, own_ids)


if __name__ == "__main__":
    unittest.main()
