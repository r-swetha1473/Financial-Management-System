"""P2P vendor API: tenant isolation, RBAC, and create+list happy path."""

from __future__ import annotations

import asyncio
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.organization import Organization
from app.models.user import User, UserSession
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorOut

VENDORS_URL = "/api/v1/p2p/vendors"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "p2p-vendor-test-"
ORG_B_PASSWORD = "isoadmin123"


def _run(coro):
    return asyncio.run(coro)


async def _with_own_session(work):
    """Use a private engine so TestClient's event loop is not reused."""
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


class VendorApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_vendor_ids: list

    @classmethod
    def setUpClass(cls) -> None:
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
                name="Vendor Isolation Org",
                slug=f"iso-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-admin",
                    email=email,
                    full_name="Isolation Admin",
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
            if cls.created_vendor_ids:
                await session.execute(delete(Vendor).where(Vendor.id.in_(cls.created_vendor_ids)))
            await session.execute(delete(Vendor).where(Vendor.name.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(Vendor).where(Vendor.organization_id == cls.org_b_id))
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

    def test_vendor_schema_exposes_only_gstin(self) -> None:
        self.assertEqual([name for name in VendorCreate.model_fields if "gst" in name.lower()], ["gstin"])
        self.assertEqual([name for name in VendorOut.model_fields if "gst" in name.lower()], ["gstin"])

    def test_admin_create_and_list_happy_path(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={
                "name": name,
                "address": "12 Warehouse Lane",
                "phone": "9990001111",
                "email": "vendor@example.test",
                "pocName": "Priya",
                "pocEmail": "priya@example.test",
                "gstin": "29AABCU9603R1ZX",
                "state": "Karnataka",
                "status": "active",
                "organizationId": "00000000-0000-0000-0000-999999999999",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()["data"]
        self.created_vendor_ids.append(created["id"])
        self.assertEqual(created["name"], name)
        self.assertEqual(created["gstin"], "29AABCU9603R1ZX")
        self.assertNotIn("gstNumber", created)
        self.assertNotIn("gst_number", created)
        self.assertEqual(created["state"], "Karnataka")
        self.assertEqual(created["organizationId"], "00000000-0000-0000-0000-000000000001")

        listed = self.client.get(f"{VENDORS_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        self.assertTrue(body.get("success"))
        ids = [item["id"] for item in body["data"]]
        self.assertIn(created["id"], ids)
        meta = body["meta"]
        self.assertGreaterEqual(meta.get("total") or 0, 1)
        self.assertEqual(meta.get("page"), 1)
        self.assertEqual(meta.get("pageSize") or meta.get("page_size"), 20)

    def test_finance_cannot_create_vendor(self) -> None:
        token = self._login("finance@demo-business.com", "finance123")
        response = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}blocked"},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_list_filters_by_search_and_status(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        unique = uuid4().hex[:8]
        active = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}{unique}-alpha", "status": "active", "email": f"alpha-{unique}@example.com"},
        )
        inactive = self.client.post(
            VENDORS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}{unique}-beta", "status": "inactive", "gstin": f"27AAAAA{unique[:5].upper()}1Z5"},
        )
        self.assertEqual(active.status_code, 201, active.text)
        self.assertEqual(inactive.status_code, 201, inactive.text)
        active_id = active.json()["data"]["id"]
        inactive_id = inactive.json()["data"]["id"]
        self.created_vendor_ids.extend([active_id, inactive_id])

        by_status = self.client.get(
            f"{VENDORS_URL}?page=1&page_size=20&status=inactive",
            headers=self._auth(token),
        )
        self.assertEqual(by_status.status_code, 200, by_status.text)
        status_ids = [item["id"] for item in by_status.json()["data"]]
        self.assertIn(inactive_id, status_ids)
        self.assertNotIn(active_id, status_ids)

        by_name = self.client.get(
            f"{VENDORS_URL}?page=1&page_size=20&search={unique}-alpha",
            headers=self._auth(token),
        )
        self.assertEqual(by_name.status_code, 200, by_name.text)
        name_ids = [item["id"] for item in by_name.json()["data"]]
        self.assertEqual(name_ids, [active_id])

        by_email = self.client.get(
            f"{VENDORS_URL}?page=1&page_size=20&search=alpha-{unique}@example.com",
            headers=self._auth(token),
        )
        self.assertEqual(by_email.status_code, 200, by_email.text)
        self.assertEqual([item["id"] for item in by_email.json()["data"]], [active_id])

    def test_vendor_created_in_org_a_is_invisible_to_org_b(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            VENDORS_URL,
            headers=self._auth(token_a),
            json={"name": name, "gstin": "27AAAAA0000A1Z5", "state": "Maharashtra"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        vendor_id = create.json()["data"]["id"]
        self.created_vendor_ids.append(vendor_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{VENDORS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(vendor_id, ids_b)

        spoof = self.client.post(
            VENDORS_URL,
            headers=self._auth(token_b),
            json={
                "name": f"{TEST_MARKER}spoof",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_vendor_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))
        self.assertNotEqual(spoofed["organizationId"], "00000000-0000-0000-0000-000000000001")

    def test_get_vendor_by_id_is_tenant_scoped(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        create = self.client.post(
            VENDORS_URL,
            headers=self._auth(token_a),
            json={"name": f"{TEST_MARKER}{uuid4().hex[:8]}", "gstin": "27AAAAA0000A1Z5"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        vendor_id = create.json()["data"]["id"]
        self.created_vendor_ids.append(vendor_id)

        fetched = self.client.get(f"{VENDORS_URL}/{vendor_id}", headers=self._auth(token_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], vendor_id)
        self.assertIn("gstin", fetched.json()["data"])
        self.assertNotIn("gstNumber", fetched.json()["data"])

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{VENDORS_URL}/{vendor_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)


if __name__ == "__main__":
    unittest.main()
