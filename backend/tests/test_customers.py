"""O2C customer API: tenant isolation, RBAC, and create+list happy path."""

from __future__ import annotations

import asyncio
import unittest
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.customer import Customer
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User, UserSession
from app.schemas.customer import CustomerCreate, CustomerOut

DOCUMENTS_URL = "/api/v1/documents"
JPEG_BYTES = b"\xff\xd8\xff\xd9"
PDF_BYTES = b"%PDF-1.4 test-proof"

CUSTOMERS_URL = "/api/v1/o2c/customers"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-customer-test-"
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


class CustomerApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_customer_ids: list

    @classmethod
    def setUpClass(cls) -> None:
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
                name="Customer Isolation Org",
                slug=f"iso-cus-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-cus-admin",
                    email=email,
                    full_name="Customer Isolation Admin",
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
            ids = list(cls.created_customer_ids)
            if ids:
                await session.execute(
                    update(Customer)
                    .where(Customer.id.in_(ids))
                    .values(photo_document_id=None, address_proof_document_id=None)
                )
                await session.execute(delete(Document).where(Document.entity_id.in_(ids)))
                await session.execute(delete(Customer).where(Customer.id.in_(ids)))
            marked = select(Customer.id).where(Customer.name.like(f"{TEST_MARKER}%"))
            marked_ids = list((await session.execute(marked)).scalars().all())
            if marked_ids:
                await session.execute(
                    update(Customer)
                    .where(Customer.id.in_(marked_ids))
                    .values(photo_document_id=None, address_proof_document_id=None)
                )
                await session.execute(delete(Document).where(Document.entity_id.in_(marked_ids)))
                await session.execute(delete(Customer).where(Customer.id.in_(marked_ids)))
            if cls.org_b_id is not None:
                org_customers = select(Customer.id).where(Customer.organization_id == cls.org_b_id)
                org_customer_ids = list((await session.execute(org_customers)).scalars().all())
                if org_customer_ids:
                    await session.execute(
                        update(Customer)
                        .where(Customer.id.in_(org_customer_ids))
                        .values(photo_document_id=None, address_proof_document_id=None)
                    )
                    await session.execute(delete(Document).where(Document.entity_id.in_(org_customer_ids)))
                await session.execute(delete(Document).where(Document.organization_id == cls.org_b_id))
                await session.execute(delete(Customer).where(Customer.organization_id == cls.org_b_id))
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

    def test_customer_schema_exposes_gstin_not_gst_number(self) -> None:
        self.assertEqual([name for name in CustomerCreate.model_fields if "gst" in name.lower()], ["gstin"])
        self.assertEqual([name for name in CustomerOut.model_fields if "gst" in name.lower()], ["gstin"])
        self.assertIn("credit_limit", CustomerCreate.model_fields)
        self.assertIn("credit_limit", CustomerOut.model_fields)

    def test_admin_create_and_list_happy_path(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={
                "name": name,
                "address": "14 MG Road, Bengaluru",
                "gstin": "29AABCU9603R1ZX",
                "state": "Karnataka",
                "creditLimit": "250000.00",
                "organizationId": "00000000-0000-0000-0000-999999999999",
                "addressProofName": "should-be-ignored.pdf",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()["data"]
        self.created_customer_ids.append(created["id"])
        self.assertEqual(created["name"], name)
        self.assertEqual(created["gstin"], "29AABCU9603R1ZX")
        self.assertNotIn("gstNumber", created)
        self.assertNotIn("gst_number", created)
        self.assertEqual(created["state"], "Karnataka")
        self.assertEqual(Decimal(str(created.get("creditLimit") or created.get("credit_limit"))), Decimal("250000.00"))
        self.assertIsNone(created.get("addressProofName") or created.get("address_proof_name"))
        self.assertIsNone(created.get("phone"))
        self.assertEqual(created["organizationId"], "00000000-0000-0000-0000-000000000001")

        listed = self.client.get(f"{CUSTOMERS_URL}?page=1&page_size=20", headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        self.assertTrue(body.get("success"))
        ids = [item["id"] for item in body["data"]]
        self.assertIn(created["id"], ids)
        meta = body["meta"]
        self.assertGreaterEqual(meta.get("total") or 0, 1)
        self.assertEqual(meta.get("page"), 1)
        self.assertEqual(meta.get("pageSize") or meta.get("page_size"), 20)

        fetched = self.client.get(f"{CUSTOMERS_URL}/{created['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["id"], created["id"])

    def test_finance_cannot_create_customer(self) -> None:
        token = self._login("finance@demo-business.com", "finance123")
        response = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}blocked"},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_customer_created_in_org_a_is_invisible_to_org_b(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token_a),
            json={"name": name, "gstin": "27AAAAA0000A1Z5", "state": "Maharashtra"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        customer_id = create.json()["data"]["id"]
        self.created_customer_ids.append(customer_id)
        self.assertIsNone(create.json()["data"].get("creditLimit") or create.json()["data"].get("credit_limit"))

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{CUSTOMERS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(customer_id, ids_b)

        stolen = self.client.get(f"{CUSTOMERS_URL}/{customer_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        spoof = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token_b),
            json={
                "name": f"{TEST_MARKER}spoof",
                "organizationId": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(spoof.status_code, 201, spoof.text)
        spoofed = spoof.json()["data"]
        self.created_customer_ids.append(spoofed["id"])
        self.assertEqual(spoofed["organizationId"], str(self.org_b_id))
        self.assertNotEqual(spoofed["organizationId"], "00000000-0000-0000-0000-000000000001")

    def test_credit_limit_rejects_non_numeric(self) -> None:
        with self.assertRaises(ValidationError):
            CustomerCreate(name="Acme", credit_limit="8998fdgdgddfgx xcvv")
        token = self._login("admin@demo-business.com", "admin123")
        response = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={"name": f"{TEST_MARKER}{uuid4().hex[:8]}", "creditLimit": "8998fdgdgddfgx xcvv"},
        )
        self.assertEqual(response.status_code, 422, response.text)
        body = response.json()
        self.assertEqual(body["code"], "422")
        self.assertIn("non-negative number", body["message"])

    def test_create_persists_phone_license_and_uploads(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={
                "name": name,
                "phone": "9876543210",
                "driversLicenseNumber": "KA01 20240012345",
                "creditLimit": "15000.00",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created = create.json()["data"]
        self.created_customer_ids.append(created["id"])
        self.assertEqual(created["phone"], "9876543210")
        self.assertEqual(created.get("driversLicenseNumber") or created.get("drivers_license_number"), "KA01 20240012345")
        self.assertEqual(Decimal(str(created.get("creditLimit") or created.get("credit_limit"))), Decimal("15000.00"))
        self.assertIsNone(created.get("gstin"))
        self.assertIsNone(created.get("photoDocumentId") or created.get("photo_document_id"))

        photo = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("face.jpg", JPEG_BYTES, "image/jpeg")},
            data={"entityName": "customer", "entityId": created["id"], "kind": "photo"},
        )
        self.assertEqual(photo.status_code, 201, photo.text)
        proof = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("id.pdf", PDF_BYTES, "application/pdf")},
            data={"entityName": "customer", "entityId": created["id"], "kind": "address_proof"},
        )
        self.assertEqual(proof.status_code, 201, proof.text)

        fetched = self.client.get(f"{CUSTOMERS_URL}/{created['id']}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        data = fetched.json()["data"]
        self.assertEqual(data["phone"], "9876543210")
        self.assertEqual(data.get("photoFileName") or data.get("photo_file_name"), "face.jpg")
        self.assertEqual(data.get("addressProofName") or data.get("address_proof_name"), "id.pdf")
        self.assertEqual(data.get("photoDocumentId") or data.get("photo_document_id"), photo.json()["data"]["id"])
        self.assertEqual(
            data.get("addressProofDocumentId") or data.get("address_proof_document_id"),
            proof.json()["data"]["id"],
        )
        content = self.client.get(
            f"{DOCUMENTS_URL}/{photo.json()['data']['id']}/content",
            headers=self._auth(token),
        )
        self.assertEqual(content.status_code, 200, content.text)
        self.assertEqual(content.content, JPEG_BYTES)


if __name__ == "__main__":
    unittest.main()
