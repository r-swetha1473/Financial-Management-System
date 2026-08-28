"""Dashboard recent tables: live tenant rows, not seed. RBAC + isolation."""

from __future__ import annotations

import asyncio
import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.collection import Collection
from app.models.customer import Customer
from app.models.finance_account import FinanceAccount
from app.models.finance_transaction import FinanceTransaction
from app.models.legacy_booking import Booking, InvoiceReceipt, LegacyInvoice
from app.models.organization import Organization
from app.models.sales_invoice import SalesInvoice
from app.models.user import User, UserSession
from tests.audit_teardown import allow_audit_delete_for_tests

LOGIN_URL = "/api/v1/auth/login"
EXPENSES_URL = "/api/v1/finance/expenses"
DASH_EXPENSES = "/api/v1/dashboard/expenses"
DASH_INVOICES = "/api/v1/dashboard/invoices"
DASH_RECEIPTS = "/api/v1/dashboard/receipts"
DASH_INCOME = "/api/v1/dashboard/income"
TEST_MARKER = "dash-recent-test-"
ORG_B_PASSWORD = "isoadmin123"
SEED_EXPENSE_IDS = {"EXP-1042", "EXP-1041", "EXP-1040"}
SEED_VENDORS = {"Metro Supplies Ltd", "TechParts India", "National Logistics"}
SEED_CUSTOMERS = {"Acme Retail Pvt Ltd", "Greenfield Motors", "Horizon Fleet"}
SEED_INVOICE_NUMBERS = {"SI-2026-0892", "SI-2026-0891", "SI-2026-0890", "SI-2026-0888", "SI-2026-0885"}
SEED_RECEIPT_IDS = {"RCP-441", "RCP-440", "RCP-439"}


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


class DashboardRecentApiTests(unittest.TestCase):
    client: TestClient
    _client_cm: object
    org_b_id = None
    org_b_email: str
    created_expense_ids: list
    created_invoice_ids: list
    created_receipt_ids: list
    created_customer_ids: list
    created_booking_ids: list
    created_legacy_invoice_ids: list

    @classmethod
    def setUpClass(cls) -> None:
        cls.created_expense_ids = []
        cls.created_invoice_ids = []
        cls.created_receipt_ids = []
        cls.created_customer_ids = []
        cls.created_booking_ids = []
        cls.created_legacy_invoice_ids = []
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()
        cls.org_b_email = f"admin-{uuid4().hex[:10]}@iso-dash.example.com"
        cls.org_b_id = _run(cls._insert_org_b(cls.org_b_email))

    @classmethod
    def tearDownClass(cls) -> None:
        _run(cls._cleanup())
        cls._client_cm.__exit__(None, None, None)

    @staticmethod
    async def _insert_org_b(email: str):
        async def work(session: AsyncSession):
            org = Organization(
                name="Dashboard Isolation Org",
                slug=f"iso-dash-{uuid4().hex[:12]}",
                is_active=True,
            )
            session.add(org)
            await session.flush()
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-dash-admin",
                    email=email,
                    full_name="Dash Isolation Admin",
                    password_hash=hash_password(ORG_B_PASSWORD),
                    role="ADMIN",
                    is_active=True,
                )
            )
            session.add(
                User(
                    organization_id=org.id,
                    username="iso-dash-viewer",
                    email=f"viewer-{email}",
                    full_name="Dash Isolation Viewer",
                    password_hash=hash_password("viewer123"),
                    role="VIEWER",
                    is_active=True,
                )
            )
            return org.id

        return await _with_own_session(work)

    @classmethod
    async def _cleanup(cls) -> None:
        async def work(session: AsyncSession):
            await allow_audit_delete_for_tests(session)
            if cls.created_receipt_ids:
                await session.execute(delete(Collection).where(Collection.id.in_(cls.created_receipt_ids)))
                await session.execute(
                    delete(InvoiceReceipt).where(InvoiceReceipt.id.in_(cls.created_receipt_ids))
                )
            if cls.created_invoice_ids:
                await session.execute(delete(SalesInvoice).where(SalesInvoice.id.in_(cls.created_invoice_ids)))
            if cls.created_legacy_invoice_ids:
                await session.execute(
                    delete(LegacyInvoice).where(LegacyInvoice.id.in_(cls.created_legacy_invoice_ids))
                )
            if cls.created_booking_ids:
                await session.execute(delete(Booking).where(Booking.id.in_(cls.created_booking_ids)))
            if cls.created_customer_ids:
                await session.execute(delete(Customer).where(Customer.id.in_(cls.created_customer_ids)))
            if cls.created_expense_ids:
                await session.execute(delete(AuditLog).where(AuditLog.entity_id.in_(cls.created_expense_ids)))
                await session.execute(
                    delete(FinanceTransaction).where(FinanceTransaction.id.in_(cls.created_expense_ids))
                )
            marked = select(FinanceTransaction.id).where(
                FinanceTransaction.description.like(f"{TEST_MARKER}%")
            )
            await session.execute(delete(FinanceTransaction).where(FinanceTransaction.id.in_(marked)))
            if cls.org_b_id is not None:
                await session.execute(delete(AuditLog).where(AuditLog.organization_id == cls.org_b_id))
                await session.execute(
                    delete(Collection).where(Collection.organization_id == cls.org_b_id)
                )
                await session.execute(
                    delete(InvoiceReceipt).where(InvoiceReceipt.organization_id == cls.org_b_id)
                )
                await session.execute(
                    delete(SalesInvoice).where(SalesInvoice.organization_id == cls.org_b_id)
                )
                await session.execute(
                    delete(LegacyInvoice).where(LegacyInvoice.organization_id == cls.org_b_id)
                )
                await session.execute(delete(Booking).where(Booking.organization_id == cls.org_b_id))
                await session.execute(delete(Customer).where(Customer.organization_id == cls.org_b_id))
                await session.execute(
                    delete(FinanceTransaction).where(FinanceTransaction.organization_id == cls.org_b_id)
                )
                await session.execute(
                    delete(FinanceAccount).where(FinanceAccount.organization_id == cls.org_b_id)
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

    def test_unauthenticated_recent_tables_are_401(self) -> None:
        for url in (DASH_EXPENSES, DASH_INVOICES, DASH_RECEIPTS, DASH_INCOME):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, response.text)

    def test_viewer_can_read_recent_tables(self) -> None:
        token = self._login("viewer@demo-business.com", "viewer123")
        for url in (DASH_EXPENSES, DASH_INVOICES, DASH_RECEIPTS, f"{DASH_INCOME}?period=monthly"):
            response = self.client.get(url, headers=self._auth(token))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsInstance(response.json()["data"], list)

    def test_empty_org_returns_no_seed_rows(self) -> None:
        token = self._login(self.org_b_email, ORG_B_PASSWORD)
        expenses = self.client.get(DASH_EXPENSES, headers=self._auth(token))
        invoices = self.client.get(DASH_INVOICES, headers=self._auth(token))
        receipts = self.client.get(DASH_RECEIPTS, headers=self._auth(token))
        self.assertEqual(expenses.status_code, 200, expenses.text)
        self.assertEqual(invoices.status_code, 200, invoices.text)
        self.assertEqual(receipts.status_code, 200, receipts.text)
        self.assertEqual(expenses.json()["data"], [])
        self.assertEqual(invoices.json()["data"], [])
        self.assertEqual(receipts.json()["data"], [])
        trend = self.client.get(f"{DASH_INCOME}?period=monthly", headers=self._auth(token))
        self.assertEqual(trend.status_code, 200, trend.text)
        points = trend.json()["data"]
        self.assertEqual(len(points), 6)
        self.assertNotIn("Jan", [row["label"] for row in points])
        self.assertNotIn("180000.00", [row["income"] for row in points])
        for row in points:
            self.assertEqual(Decimal(str(row["income"])), Decimal("0"))
            self.assertEqual(Decimal(str(row["expenses"])), Decimal("0"))

    def test_trend_posts_expense_in_current_bucket_and_isolates_tenants(self) -> None:
        demo = self._login("admin@demo-business.com", "admin123")
        other = self._login(self.org_b_email, ORG_B_PASSWORD)
        today = date.today().isoformat()
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(demo),
            json={
                "cost": "33.5000",
                "expenseDate": today,
                "productServiceName": f"{TEST_MARKER}trend",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        self.created_expense_ids.append(create.json()["data"]["id"])

        monthly = self.client.get(f"{DASH_INCOME}?period=monthly", headers=self._auth(demo))
        self.assertEqual(monthly.status_code, 200, monthly.text)
        last = monthly.json()["data"][-1]
        self.assertGreaterEqual(Decimal(str(last["expenses"])), Decimal("33.5000"))
        self.assertNotEqual(last["expenses"], "207000.00")

        daily = self.client.get(f"{DASH_INCOME}?period=daily", headers=self._auth(demo))
        self.assertEqual(daily.status_code, 200, daily.text)
        self.assertEqual(len(daily.json()["data"]), 7)
        self.assertGreaterEqual(Decimal(str(daily.json()["data"][-1]["expenses"])), Decimal("33.5000"))

        isolated = self.client.get(f"{DASH_INCOME}?period=monthly", headers=self._auth(other))
        self.assertEqual(isolated.status_code, 200, isolated.text)
        for row in isolated.json()["data"]:
            self.assertEqual(Decimal(str(row["expenses"])), Decimal("0"))

    def test_recent_expense_happy_path_and_not_seed(self) -> None:
        token = self._login("admin@demo-business.com", "admin123")
        description = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(token),
            json={
                "cost": "77.2500",
                "expenseDate": "2026-08-28",
                "productServiceName": description,
                "vendorId": "",
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created_id = create.json()["data"]["id"]
        self.created_expense_ids.append(created_id)

        listed = self.client.get(DASH_EXPENSES, headers=self._auth(token))
        self.assertEqual(listed.status_code, 200, listed.text)
        rows = listed.json()["data"]
        ids = {row["id"] for row in rows}
        self.assertIn(created_id, ids)
        self.assertTrue(ids.isdisjoint(SEED_EXPENSE_IDS))
        vendors = {row["vendor"] for row in rows}
        self.assertTrue(vendors.isdisjoint(SEED_VENDORS))
        match = next(row for row in rows if row["id"] == created_id)
        self.assertEqual(Decimal(str(match["amount"])), Decimal("77.2500"))
        self.assertEqual(match["expenseDate"], "2026-08-28")
        self.assertEqual(match["category"], "—")
        self.assertEqual(match["status"], "posted")

    def test_recent_invoice_and_receipt_happy_path(self) -> None:
        token = self._login(self.org_b_email, ORG_B_PASSWORD)
        invoice_number = f"SI-DASH-{uuid4().hex[:8]}"
        legacy_number = f"LEG-DASH-{uuid4().hex[:8]}"
        ids = _run(self._insert_invoice_and_receipts(invoice_number, legacy_number))
        self.created_customer_ids.append(ids["customer_id"])
        self.created_invoice_ids.append(ids["invoice_id"])
        self.created_receipt_ids.append(ids["collection_id"])
        self.created_booking_ids.append(ids["booking_id"])
        self.created_legacy_invoice_ids.append(ids["legacy_invoice_id"])
        self.created_receipt_ids.append(ids["legacy_receipt_id"])

        invoices = self.client.get(DASH_INVOICES, headers=self._auth(token))
        self.assertEqual(invoices.status_code, 200, invoices.text)
        invoice_rows = invoices.json()["data"]
        numbers = {row["invoiceNumber"] for row in invoice_rows}
        self.assertIn(invoice_number, numbers)
        self.assertIn(legacy_number, numbers)
        self.assertTrue(numbers.isdisjoint(SEED_INVOICE_NUMBERS))
        customers = {row["customer"] for row in invoice_rows}
        self.assertTrue(customers.isdisjoint(SEED_CUSTOMERS))
        o2c = next(row for row in invoice_rows if row["invoiceNumber"] == invoice_number)
        self.assertEqual(o2c["status"], "pending")
        self.assertEqual(Decimal(str(o2c["amount"])), Decimal("500.0000"))

        receipts = self.client.get(DASH_RECEIPTS, headers=self._auth(token))
        self.assertEqual(receipts.status_code, 200, receipts.text)
        receipt_rows = receipts.json()["data"]
        receipt_ids = {row["id"] for row in receipt_rows}
        self.assertIn(ids["collection_id"], receipt_ids)
        self.assertIn(ids["legacy_receipt_id"], receipt_ids)
        self.assertTrue(receipt_ids.isdisjoint(SEED_RECEIPT_IDS))
        modes = {row["paymentMode"] for row in receipt_rows}
        self.assertIn("UPI", modes)
        self.assertIn("Cash", modes)

    def test_tenant_isolation_hides_other_org_rows(self) -> None:
        demo = self._login("admin@demo-business.com", "admin123")
        other = self._login(self.org_b_email, ORG_B_PASSWORD)
        description = f"{TEST_MARKER}{uuid4().hex[:8]}"
        create = self.client.post(
            EXPENSES_URL,
            headers=self._auth(demo),
            json={
                "cost": "12.0000",
                "expenseDate": "2026-08-28",
                "productServiceName": description,
            },
        )
        self.assertEqual(create.status_code, 201, create.text)
        created_id = create.json()["data"]["id"]
        self.created_expense_ids.append(created_id)

        demo_rows = self.client.get(DASH_EXPENSES, headers=self._auth(demo)).json()["data"]
        other_rows = self.client.get(DASH_EXPENSES, headers=self._auth(other)).json()["data"]
        self.assertIn(created_id, {row["id"] for row in demo_rows})
        self.assertNotIn(created_id, {row["id"] for row in other_rows})

        stolen = self.client.get(DASH_INVOICES, headers=self._auth(other))
        self.assertEqual(stolen.status_code, 200, stolen.text)
        demo_invoices = self.client.get(DASH_INVOICES, headers=self._auth(demo)).json()["data"]
        other_invoices = stolen.json()["data"]
        demo_ids = {row["id"] for row in demo_invoices}
        other_ids = {row["id"] for row in other_invoices}
        self.assertTrue(demo_ids.isdisjoint(other_ids))

    async def _insert_invoice_and_receipts(self, invoice_number: str, legacy_number: str):
        async def work(session: AsyncSession):
            customer = Customer(
                organization_id=self.org_b_id,
                name=f"{TEST_MARKER}customer",
            )
            session.add(customer)
            await session.flush()
            invoice = SalesInvoice(
                organization_id=self.org_b_id,
                customer_id=customer.id,
                invoice_number=invoice_number,
                status="pending",
                invoice_date=date(2026, 8, 28),
                amount=Decimal("500.0000"),
            )
            session.add(invoice)
            await session.flush()
            collection = Collection(
                organization_id=self.org_b_id,
                sales_invoice_id=invoice.id,
                collection_date=date(2026, 8, 28),
                amount=Decimal("200.0000"),
                payment_mode="UPI",
                status="completed",
            )
            session.add(collection)
            booking = Booking(
                organization_id=self.org_b_id,
                customer_id=customer.id,
                booking_start_date=date(2026, 8, 1),
            )
            session.add(booking)
            await session.flush()
            legacy = LegacyInvoice(
                organization_id=self.org_b_id,
                invoice_number=legacy_number,
                customer_id=customer.id,
                booking_id=booking.id,
                invoice_raised_date=date(2026, 8, 27),
                invoice_amount=Decimal("300.0000"),
            )
            session.add(legacy)
            await session.flush()
            receipt = InvoiceReceipt(
                organization_id=self.org_b_id,
                invoice_id=legacy.id,
                receipt_date=date(2026, 8, 27),
                receipt_amount=Decimal("300.0000"),
                payment_mode="Cash",
            )
            session.add(receipt)
            await session.flush()
            return {
                "customer_id": str(customer.id),
                "invoice_id": str(invoice.id),
                "collection_id": str(collection.id),
                "booking_id": str(booking.id),
                "legacy_invoice_id": str(legacy.id),
                "legacy_receipt_id": str(receipt.id),
            }

        return await _with_own_session(work)


if __name__ == "__main__":
    unittest.main()
