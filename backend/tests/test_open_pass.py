"""Open-pass APIs: catalog, legacy bookings, finance surfaces, reports, reference data."""

from __future__ import annotations

import asyncio
import unittest
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.catalog import Category, Offering, Product, Subcategory
from app.models.customer import Customer
from app.models.finance_account import FinanceAccount
from app.models.legacy_booking import Booking, InvoiceReceipt, LegacyInvoice
from app.models.organization import Organization
from app.models.reconciliation_note import ReconciliationNote
from app.models.reference_data import ReferenceData
from app.models.user import User, UserSession

LOGIN_URL = "/api/v1/auth/login"
PRODUCTS_URL = "/api/v1/products"
CATEGORIES_URL = "/api/v1/categories"
OFFERINGS_URL = "/api/v1/offerings"
BOOKINGS_URL = "/api/v1/bookings"
INVOICES_URL = "/api/v1/invoices"
RECEIPTS_URL = "/api/v1/receipts"
CUSTOMERS_URL = "/api/v1/o2c/customers"
ACCOUNTS_URL = "/api/v1/finance/accounts"
TRANSACTIONS_URL = "/api/v1/finance/transactions"
INCOME_URL = "/api/v1/finance/income"
GST_URL = "/api/v1/finance/gst/summary"
RECON_URL = "/api/v1/finance/reconciliation/note"
REPORTS_URL = "/api/v1/reports"
REFERENCE_URL = "/api/v1/reference-data"
TEST_MARKER = "open-pass-test-"
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


class OpenPassApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_ids: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_ids = {
            "products": [],
            "categories": [],
            "offerings": [],
            "customers": [],
            "bookings": [],
            "invoices": [],
            "receipts": [],
            "reference": [],
        }
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-open.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Open Pass Isolation Org",
                slug=f"iso-open-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-open-admin",
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
            if cls.created_ids["receipts"]:
                await session.execute(delete(InvoiceReceipt).where(InvoiceReceipt.id.in_(cls.created_ids["receipts"])))
            if cls.created_ids["invoices"]:
                await session.execute(delete(LegacyInvoice).where(LegacyInvoice.id.in_(cls.created_ids["invoices"])))
            if cls.created_ids["bookings"]:
                await session.execute(delete(Booking).where(Booking.id.in_(cls.created_ids["bookings"])))
            if cls.created_ids["offerings"]:
                await session.execute(delete(Offering).where(Offering.id.in_(cls.created_ids["offerings"])))
            if cls.created_ids["products"]:
                await session.execute(delete(Product).where(Product.id.in_(cls.created_ids["products"])))
            if cls.created_ids["categories"]:
                await session.execute(delete(Subcategory).where(Subcategory.category_id.in_(cls.created_ids["categories"])))
                await session.execute(delete(Category).where(Category.id.in_(cls.created_ids["categories"])))
            if cls.created_ids["reference"]:
                await session.execute(delete(ReferenceData).where(ReferenceData.id.in_(cls.created_ids["reference"])))
            if cls.created_ids["customers"]:
                await session.execute(delete(Customer).where(Customer.id.in_(cls.created_ids["customers"])))
            marked_products = select(Product.id).where(Product.name.like(f"{TEST_MARKER}%"))
            await session.execute(delete(Offering).where(Offering.product_id.in_(marked_products)))
            await session.execute(delete(Product).where(Product.name.like(f"{TEST_MARKER}%")))
            await session.execute(delete(Category).where(Category.name.like(f"{TEST_MARKER}%")))
            await session.execute(delete(ReferenceData).where(ReferenceData.code.like(f"{TEST_MARKER}%")))
            await session.execute(delete(Customer).where(Customer.name.like(f"{TEST_MARKER}%")))
            if cls.org_b_id is not None:
                await session.execute(delete(InvoiceReceipt).where(InvoiceReceipt.organization_id == cls.org_b_id))
                await session.execute(delete(LegacyInvoice).where(LegacyInvoice.organization_id == cls.org_b_id))
                await session.execute(delete(Booking).where(Booking.organization_id == cls.org_b_id))
                await session.execute(delete(Offering).where(Offering.organization_id == cls.org_b_id))
                await session.execute(delete(Product).where(Product.organization_id == cls.org_b_id))
                await session.execute(delete(Subcategory).where(Subcategory.organization_id == cls.org_b_id))
                await session.execute(delete(Category).where(Category.organization_id == cls.org_b_id))
                await session.execute(delete(ReferenceData).where(ReferenceData.organization_id == cls.org_b_id))
                await session.execute(delete(ReconciliationNote).where(ReconciliationNote.organization_id == cls.org_b_id))
                await session.execute(delete(Customer).where(Customer.organization_id == cls.org_b_id))
                await session.execute(delete(FinanceAccount).where(FinanceAccount.organization_id == cls.org_b_id))
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

    def test_catalog_create_list_and_isolation(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        name = f"{TEST_MARKER}{uuid4().hex[:8]}"
        created = self.client.post(PRODUCTS_URL, headers=self._auth(token_a), json={"name": name, "status": "active"})
        self.assertEqual(created.status_code, 201, created.text)
        product_id = created.json()["data"]["id"]
        self.created_ids["products"].append(product_id)

        listed = self.client.get(f"{PRODUCTS_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(product_id, [row["id"] for row in listed.json()["data"]])

        cat = self.client.post(
            CATEGORIES_URL,
            headers=self._auth(token_a),
            json={"name": name, "description": "test", "isActive": True},
        )
        self.assertEqual(cat.status_code, 201, cat.text)
        self.created_ids["categories"].append(cat.json()["data"]["id"])

        offering = self.client.post(
            OFFERINGS_URL,
            headers=self._auth(token_a),
            json={"name": name, "productId": product_id, "amount": "100.0000", "isActive": True},
        )
        self.assertEqual(offering.status_code, 201, offering.text)
        self.created_ids["offerings"].append(offering.json()["data"]["id"])
        self.assertEqual(offering.json()["data"]["productId"], product_id)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{PRODUCTS_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(product_id, [row["id"] for row in listed_b.json()["data"]])
        stolen = self.client.get(f"{PRODUCTS_URL}/{product_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)

        viewer = self._login("viewer@demo-business.com", "viewer123")
        blocked = self.client.post(PRODUCTS_URL, headers=self._auth(viewer), json={"name": f"{TEST_MARKER}blocked"})
        self.assertEqual(blocked.status_code, 403, blocked.text)

        operator = self._login("operator@demo-business.com", "operator123")
        op_product = self.client.post(
            PRODUCTS_URL,
            headers=self._auth(operator),
            json={"name": f"{TEST_MARKER}op-sku", "status": "active"},
        )
        self.assertEqual(op_product.status_code, 201, op_product.text)
        self.created_ids["products"].append(op_product.json()["data"]["id"])
        op_category = self.client.post(
            CATEGORIES_URL,
            headers=self._auth(operator),
            json={"name": f"{TEST_MARKER}op-cat", "isActive": True},
        )
        self.assertEqual(op_category.status_code, 201, op_category.text)
        self.created_ids["categories"].append(op_category.json()["data"]["id"])

    def test_legacy_booking_invoice_receipt_and_isolation(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        customer = self.client.post(
            CUSTOMERS_URL,
            headers=self._auth(token_a),
            json={"name": f"{TEST_MARKER}{uuid4().hex[:8]}"},
        )
        self.assertEqual(customer.status_code, 201, customer.text)
        customer_id = customer.json()["data"]["id"]
        self.created_ids["customers"].append(customer_id)

        booking = self.client.post(
            BOOKINGS_URL,
            headers=self._auth(token_a),
            json={
                "customerId": customer_id,
                "bookingStartDate": "2026-08-01",
                "bookingEndDate": "2026-08-31",
                "securityPaid": "500.0000",
            },
        )
        self.assertEqual(booking.status_code, 201, booking.text)
        booking_id = booking.json()["data"]["id"]
        self.created_ids["bookings"].append(booking_id)
        self.assertEqual(booking.json()["data"]["customerId"], customer_id)

        invoice_number = f"INV-OPEN-{uuid4().hex[:8]}"
        invoice = self.client.post(
            INVOICES_URL,
            headers=self._auth(token_a),
            json={
                "invoiceNumber": invoice_number,
                "customerId": customer_id,
                "bookingId": booking_id,
                "invoiceRaisedDate": "2026-08-02",
                "invoiceAmount": "1000.0000",
                "isGstInvoice": True,
                "gstAmount": "180.0000",
            },
        )
        self.assertEqual(invoice.status_code, 201, invoice.text)
        invoice_id = invoice.json()["data"]["id"]
        self.created_ids["invoices"].append(invoice_id)
        self.assertEqual(invoice.json()["data"]["gstAmount"], "180.0000")
        self.assertEqual(invoice.json()["data"]["status"], "pending")
        self.assertEqual(Decimal(str(invoice.json()["data"]["outstanding"])), Decimal("1000.0000"))

        receipt = self.client.post(
            RECEIPTS_URL,
            headers=self._auth(token_a),
            json={
                "invoiceId": invoice_id,
                "receiptDate": "2026-08-03",
                "receiptAmount": "400.0000",
                "paymentMode": "Cash",
            },
        )
        self.assertEqual(receipt.status_code, 201, receipt.text)
        self.created_ids["receipts"].append(receipt.json()["data"]["id"])

        fetched = self.client.get(f"{INVOICES_URL}/{invoice_id}", headers=self._auth(token_a))
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["data"]["status"], "partially_paid")
        self.assertEqual(Decimal(str(fetched.json()["data"]["outstanding"])), Decimal("600.0000"))

        overpay = self.client.post(
            RECEIPTS_URL,
            headers=self._auth(token_a),
            json={
                "invoiceId": invoice_id,
                "receiptDate": "2026-08-04",
                "receiptAmount": "900.0000",
                "paymentMode": "Cash",
            },
        )
        self.assertEqual(overpay.status_code, 400, overpay.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        stolen = self.client.get(f"{BOOKINGS_URL}/{booking_id}", headers=self._auth(token_b))
        self.assertEqual(stolen.status_code, 404, stolen.text)
        stolen_inv = self.client.get(f"{INVOICES_URL}/{invoice_id}", headers=self._auth(token_b))
        self.assertEqual(stolen_inv.status_code, 404, stolen_inv.text)

        viewer = self._login("viewer@demo-business.com", "viewer123")
        blocked = self.client.post(
            BOOKINGS_URL,
            headers=self._auth(viewer),
            json={"customerId": customer_id, "bookingStartDate": "2026-08-01"},
        )
        self.assertEqual(blocked.status_code, 403, blocked.text)

    def test_accounts_transactions_income_gst_recon_reports(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        accounts = self.client.get(ACCOUNTS_URL, headers=self._auth(token))
        self.assertEqual(accounts.status_code, 200, accounts.text)
        rows = accounts.json()["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Operating cash")
        self.assertIn("balance", rows[0])

        txns = self.client.get(TRANSACTIONS_URL, headers=self._auth(token))
        self.assertEqual(txns.status_code, 200, txns.text)
        self.assertTrue(txns.json().get("success"))

        income = self.client.get(INCOME_URL, headers=self._auth(token))
        self.assertEqual(income.status_code, 200, income.text)
        for row in income.json()["data"]:
            self.assertIn(row["sourceType"], ("collection", "receipt"))

        gst = self.client.get(GST_URL, headers=self._auth(token))
        self.assertEqual(gst.status_code, 200, gst.text)
        body = gst.json()["data"]
        self.assertEqual(body["expenses"], "0.0000")
        self.assertIn("inputGst", body)
        self.assertIn("outputGst", body)
        self.assertIn("supplier", body)

        note = self.client.get(RECON_URL, headers=self._auth(token))
        self.assertEqual(note.status_code, 200, note.text)

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        saved = self.client.put(RECON_URL, headers=self._auth(token_b), json={"note": f"{TEST_MARKER}hello"})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["data"]["note"], f"{TEST_MARKER}hello")

        viewer = self._login("viewer@demo-business.com", "viewer123")
        blocked_note = self.client.put(RECON_URL, headers=self._auth(viewer), json={"note": "nope"})
        self.assertEqual(blocked_note.status_code, 403, blocked_note.text)

        for key in ("p2p", "o2c", "payables", "receivables", "gst", "cash-flow", "financial-summary"):
            report = self.client.get(f"{REPORTS_URL}/{key}", headers=self._auth(token))
            self.assertEqual(report.status_code, 200, f"{key}: {report.text}")
            self.assertTrue(report.json()["data"]["title"])

        gst_report = self.client.get(f"{REPORTS_URL}/gst", headers=self._auth(token))
        self.assertEqual(gst_report.json()["data"]["title"], "GST summary")
        self.assertEqual(len(gst_report.json()["data"]["rows"]), 3)

        gst_b = self.client.get(GST_URL, headers=self._auth(token_b))
        self.assertEqual(gst_b.status_code, 200, gst_b.text)
        self.assertEqual(gst_b.json()["data"]["inputGst"], "0.0000")
        self.assertEqual(gst_b.json()["data"]["outputGst"], "0.0000")
        accounts_b = self.client.get(ACCOUNTS_URL, headers=self._auth(token_b))
        self.assertEqual(accounts_b.status_code, 200, accounts_b.text)
        self.assertEqual(accounts_b.json()["data"][0]["name"], "Operating cash")

    def test_reference_data_rbac_and_isolation(self) -> None:
        token_a = self._login("admin@demo-business.com", "admin123")
        code = f"{TEST_MARKER}{uuid4().hex[:8]}"
        created = self.client.post(
            REFERENCE_URL,
            headers=self._auth(token_a),
            json={"dataType": "payment_mode", "code": code, "label": "Test", "isActive": True},
        )
        self.assertEqual(created.status_code, 201, created.text)
        ref_id = created.json()["data"]["id"]
        self.created_ids["reference"].append(ref_id)

        listed = self.client.get(f"{REFERENCE_URL}?page=1&page_size=100", headers=self._auth(token_a))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn(ref_id, [row["id"] for row in listed.json()["data"]])

        token_b = self._login(self.org_b_email, ORG_B_PASSWORD)
        listed_b = self.client.get(f"{REFERENCE_URL}?page=1&page_size=100", headers=self._auth(token_b))
        self.assertEqual(listed_b.status_code, 200, listed_b.text)
        self.assertNotIn(ref_id, [row["id"] for row in listed_b.json()["data"]])

        viewer = self._login("viewer@demo-business.com", "viewer123")
        blocked = self.client.post(
            REFERENCE_URL,
            headers=self._auth(viewer),
            json={"dataType": "payment_mode", "code": f"{TEST_MARKER}nope", "label": "Nope"},
        )
        self.assertEqual(blocked.status_code, 403, blocked.text)

        finance = self._login("finance@demo-business.com", "finance123")
        blocked_finance = self.client.post(
            REFERENCE_URL,
            headers=self._auth(finance),
            json={"dataType": "payment_mode", "code": f"{TEST_MARKER}fin", "label": "Fin"},
        )
        self.assertEqual(blocked_finance.status_code, 403, blocked_finance.text)


if __name__ == "__main__":
    unittest.main()
