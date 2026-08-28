"""Authenticated document upload/download: storage_key + tenant ownership on every fetch."""

from __future__ import annotations

import asyncio
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.customer import Customer
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User, UserSession

CUSTOMERS_URL = "/api/v1/o2c/customers"
DOCUMENTS_URL = "/api/v1/documents"
LOGIN_URL = "/api/v1/auth/login"
TEST_MARKER = "o2c-doc-test-"
ORG_B_PASSWORD = "isoadmin123"
JPEG_BYTES = b"\xff\xd8\xff\xd9"
PDF_BYTES = b"%PDF-1.4 test-proof"


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


class DocumentApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_customer_ids: list
    created_document_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_customer_ids = []
        cls.created_document_ids = []
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-doc.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Document Isolation Org",
                slug=f"iso-doc-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-doc-admin",
                    email=email,
                    full_name="Document Isolation Admin",
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
            await session.execute(delete(Customer).where(Customer.name.like(f"{TEST_MARKER}%")))
            if cls.created_document_ids:
                await session.execute(delete(Document).where(Document.id.in_(cls.created_document_ids)))
            if cls.org_b_id is not None:
                await session.execute(delete(Customer).where(Customer.organization_id == cls.org_b_id))
                await session.execute(delete(Document).where(Document.organization_id == cls.org_b_id))
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
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token),
            json={"name": name, "phone": "9876543210"},
        )
        self.assertEqual(create.status_code, 201, create.text)
        customer_id = create.json()["data"]["id"]
        self.created_customer_ids.append(customer_id)
        return customer_id

    def test_upload_and_download_round_trip(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(token)
        upload = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("face.jpg", JPEG_BYTES, "image/jpeg")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        body = upload.json()["data"]
        self.created_document_ids.append(body["id"])
        self.assertEqual(body["entityName"], "customer")
        self.assertEqual(body["fileName"], "face.jpg")
        self.assertIn(str(body["organizationId"]), body["storageKey"])
        self.assertIn("photo", body["storageKey"])
        self.assertNotIn("url", body)
        self.assertNotIn("fileData", body)
        self.assertNotIn("file_data", body)

        meta = self.client.get(f"{DOCUMENTS_URL}/{body['id']}", headers=self._auth(token))
        self.assertEqual(meta.status_code, 200, meta.text)
        self.assertEqual(meta.json()["data"]["storageKey"], body["storageKey"])
        self.assertNotIn("url", meta.json()["data"])

        content = self.client.get(f"{DOCUMENTS_URL}/{body['id']}/content", headers=self._auth(token))
        self.assertEqual(content.status_code, 200, content.text)
        self.assertEqual(content.content, JPEG_BYTES)
        self.assertTrue(content.headers.get("content-type", "").startswith("image/jpeg"))

        fetched = self.client.get(f"{CUSTOMERS_URL}/{customer_id}", headers=self._auth(token))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        customer = fetched.json()["data"]
        self.assertEqual(customer.get("photoDocumentId") or customer.get("photo_document_id"), body["id"])
        self.assertEqual(customer.get("photoFileName") or customer.get("photo_file_name"), "face.jpg")

    def test_address_proof_pdf_attaches_to_customer(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(token)
        upload = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("id.pdf", PDF_BYTES, "application/pdf")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "address_proof"},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        doc_id = upload.json()["data"]["id"]
        self.created_document_ids.append(doc_id)
        fetched = self.client.get(f"{CUSTOMERS_URL}/{customer_id}", headers=self._auth(token))
        data = fetched.json()["data"]
        self.assertEqual(data.get("addressProofDocumentId") or data.get("address_proof_document_id"), doc_id)
        self.assertEqual(data.get("addressProofName") or data.get("address_proof_name"), "id.pdf")

    def test_unauthenticated_download_is_401(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(token)
        upload = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("face.jpg", JPEG_BYTES, "image/jpeg")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        doc_id = upload.json()["data"]["id"]
        self.created_document_ids.append(doc_id)
        stolen = self.client.get(f"{DOCUMENTS_URL}/{doc_id}/content")
        self.assertEqual(stolen.status_code, 401, stolen.text)

    def test_other_tenant_cannot_download(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(token_a)
        upload = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token_a),
            files={"file": ("face.jpg", JPEG_BYTES, "image/jpeg")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        doc_id = upload.json()["data"]["id"]
        self.created_document_ids.append(doc_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        meta = self.client.get(f"{DOCUMENTS_URL}/{doc_id}", headers=self._auth(token_b))
        self.assertEqual(meta.status_code, 404, meta.text)
        content = self.client.get(f"{DOCUMENTS_URL}/{doc_id}/content", headers=self._auth(token_b))
        self.assertEqual(content.status_code, 404, content.text)

        listed_b = self.client.get(f"{DOCUMENTS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        ids_b = [item["id"] for item in listed_b.json()["data"]]
        self.assertNotIn(doc_id, ids_b)

        listed_a = self.client.get(f"{DOCUMENTS_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed_a.status_code, 200, listed_a.text)
        ids_a = [item["id"] for item in listed_a.json()["data"]]
        self.assertIn(doc_id, ids_a)

    def test_viewer_cannot_upload(self) -> None:
        admin = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(admin)
        viewer = self._login("viewer@demo-business.com", "viewer123")
        upload = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(viewer),
            files={"file": ("face.jpg", JPEG_BYTES, "image/jpeg")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(upload.status_code, 403, upload.text)

    def test_rejects_wrong_type_and_oversized(self) -> None:
        from app.services.document_service import MAX_UPLOAD_BYTES

        token = self._login("admin@demo-business.com", "admin123")
        customer_id = self._create_customer(token)
        gif = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("x.gif", b"GIF89a", "image/gif")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(gif.status_code, 422, gif.text)
        self.assertIn("PNG", gif.json()["message"])
        self.assertIn("JPEG", gif.json()["message"])

        txt = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("notes.txt", b"hello", "text/plain")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "address_proof"},
        )
        self.assertEqual(txt.status_code, 422, txt.text)
        self.assertIn("PDF", txt.json()["message"])

        pdf_as_photo = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("id.pdf", PDF_BYTES, "application/pdf")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(pdf_as_photo.status_code, 422, pdf_as_photo.text)

        huge = self.client.post(
            DOCUMENTS_URL,
            headers=self._auth(token),
            files={"file": ("face.jpg", b"\xff\xd8" + b"x" * (MAX_UPLOAD_BYTES), "image/jpeg")},
            data={"entityName": "customer", "entityId": customer_id, "kind": "photo"},
        )
        self.assertEqual(huge.status_code, 422, huge.text)
        self.assertIn("10 MB", huge.json()["message"])


if __name__ == "__main__":
    unittest.main()
