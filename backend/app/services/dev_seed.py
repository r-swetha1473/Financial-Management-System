"""Development seed data — replace with database queries in later phases."""

from app.schemas.dashboard import (
    DashboardCategoryBreakdown,
    DashboardTrendPoint,
    ProductFinancialSummary,
    RecentExpenseRow,
    RecentInvoiceRow,
    RecentReceiptRow,
)


def get_income_expense_trend(period: str = "monthly") -> list[DashboardTrendPoint]:
    labels = {
        "daily": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "weekly": ["W1", "W2", "W3", "W4"],
        "monthly": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    }.get(period, ["Jan", "Feb", "Mar", "Apr", "May", "Jun"])

    income_values = ["180000.00", "222000.00", "264000.00", "306000.00", "348000.00", "390000.00", "432000.00"]
    expense_values = ["95000.00", "123000.00", "151000.00", "179000.00", "207000.00", "235000.00", "263000.00"]

    return [
        DashboardTrendPoint(
            label=label,
            income=income_values[index],
            expenses=expense_values[index],
        )
        for index, label in enumerate(labels)
    ]


def get_expense_categories() -> list[DashboardCategoryBreakdown]:
    return [
        DashboardCategoryBreakdown(category="Procurement", amount="520000.00", percentage="32.0"),
        DashboardCategoryBreakdown(category="Operations", amount="410000.00", percentage="25.3"),
        DashboardCategoryBreakdown(category="Maintenance", amount="280000.00", percentage="17.2"),
        DashboardCategoryBreakdown(category="Logistics", amount="213400.00", percentage="13.1"),
        DashboardCategoryBreakdown(category="Other", amount="200000.00", percentage="12.4"),
    ]


def get_recent_expenses() -> list[RecentExpenseRow]:
    return [
        RecentExpenseRow(
            id="EXP-1042",
            vendor="Metro Supplies Ltd",
            category="Procurement",
            amount="24500.00",
            expense_date="2026-08-24",
            status="approved",
        ),
        RecentExpenseRow(
            id="EXP-1041",
            vendor="TechParts India",
            category="Maintenance",
            amount="12800.00",
            expense_date="2026-08-23",
            status="pending",
        ),
        RecentExpenseRow(
            id="EXP-1040",
            vendor="National Logistics",
            category="Logistics",
            amount="18650.00",
            expense_date="2026-08-22",
            status="approved",
        ),
    ]


def get_recent_invoices() -> list[RecentInvoiceRow]:
    return [
        RecentInvoiceRow(
            id="INV-892",
            invoice_number="SI-2026-0892",
            customer="Acme Retail Pvt Ltd",
            amount="78500.00",
            raised_date="2026-08-22",
            status="partially_paid",
        ),
        RecentInvoiceRow(
            id="INV-891",
            invoice_number="SI-2026-0891",
            customer="Greenfield Motors",
            amount="142000.00",
            raised_date="2026-08-21",
            status="pending",
        ),
        RecentInvoiceRow(
            id="INV-890",
            invoice_number="SI-2026-0890",
            customer="Horizon Fleet",
            amount="56000.00",
            raised_date="2026-08-20",
            status="paid",
        ),
    ]


def get_recent_receipts() -> list[RecentReceiptRow]:
    return [
        RecentReceiptRow(
            id="RCP-441",
            invoice_number="SI-2026-0892",
            amount="40000.00",
            receipt_date="2026-08-24",
            payment_mode="UPI",
        ),
        RecentReceiptRow(
            id="RCP-440",
            invoice_number="SI-2026-0888",
            amount="95000.00",
            receipt_date="2026-08-23",
            payment_mode="Card",
        ),
        RecentReceiptRow(
            id="RCP-439",
            invoice_number="SI-2026-0885",
            amount="22000.00",
            receipt_date="2026-08-22",
            payment_mode="Cash",
        ),
    ]


def get_product_summaries() -> list[ProductFinancialSummary]:
    return [
        ProductFinancialSummary(
            product_id="PRD-001",
            product_name="Electric Scooter Model A",
            total_income="890000.00",
            total_expenses="412000.00",
            net="478000.00",
        ),
        ProductFinancialSummary(
            product_id="PRD-002",
            product_name="Electric Scooter Model B",
            total_income="654000.00",
            total_expenses="398000.00",
            net="256000.00",
        ),
        ProductFinancialSummary(
            product_id="PRD-003",
            product_name="Service Plan Annual",
            total_income="312000.00",
            total_expenses="84000.00",
            net="228000.00",
        ),
    ]
