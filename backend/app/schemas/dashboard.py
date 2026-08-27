"""Dashboard schemas — money fields are strings to avoid float JSON encoding."""

from app.schemas.common import CamelModel


class DashboardSummary(CamelModel):
    total_income: str
    total_expenses: str
    cash_in_hand: str
    outstanding_receivables: str
    outstanding_payables: str
    currency: str = "INR"


class DashboardTrendPoint(CamelModel):
    label: str
    income: str
    expenses: str


class DashboardCategoryBreakdown(CamelModel):
    category: str
    amount: str
    percentage: str


class RecentExpenseRow(CamelModel):
    id: str
    vendor: str
    category: str
    amount: str
    expense_date: str
    status: str


class RecentInvoiceRow(CamelModel):
    id: str
    invoice_number: str
    customer: str
    amount: str
    raised_date: str
    status: str


class RecentReceiptRow(CamelModel):
    id: str
    invoice_number: str
    amount: str
    receipt_date: str
    payment_mode: str


class CashPositionItem(CamelModel):
    account_name: str
    account_type: str
    balance: str


class ProductFinancialSummary(CamelModel):
    product_id: str
    product_name: str
    total_income: str
    total_expenses: str
    net: str
