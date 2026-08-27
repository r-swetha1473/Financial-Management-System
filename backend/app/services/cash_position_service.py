"""Cash-basis position: collections + receipts − expenses − payments.

Recorded decision: cash in hand is money in minus money out. P2P payments and
O2C collections do not post to finance_transactions, so they are counted here.
This service is the cross-module cash view, not a GL posting engine.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import CashPositionItem, DashboardSummary


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")


def _as_money(value: object) -> Decimal:
    return Decimal(str(value if value is not None else 0))


@dataclass(frozen=True)
class CashPositionSnapshot:
    expenses: Decimal
    payments: Decimal
    collections: Decimal
    receipts: Decimal
    outstanding_receivables: Decimal
    outstanding_payables: Decimal

    @property
    def net(self) -> Decimal:
        return self.collections + self.receipts - self.expenses - self.payments

    @property
    def total_income(self) -> Decimal:
        return self.collections + self.receipts

    @property
    def total_outflow(self) -> Decimal:
        return self.expenses + self.payments


# One round-trip: four independent SUMs plus two outstanding aggregates.
# Each subquery is tenant-scoped; no per-row N+1.
_COMPUTE_SQL = text(
    """
    SELECT
      (SELECT COALESCE(SUM(amount), 0)
         FROM finance_transactions
        WHERE organization_id = :org_id
          AND transaction_type = 'debit') AS expenses,
      (SELECT COALESCE(SUM(amount), 0)
         FROM p2p_payments
        WHERE organization_id = :org_id
          AND status = 'completed') AS payments,
      (SELECT COALESCE(SUM(amount), 0)
         FROM o2c_collections
        WHERE organization_id = :org_id
          AND status = 'completed') AS collections,
      (SELECT COALESCE(SUM(receipt_amount), 0)
         FROM invoice_receipts
        WHERE organization_id = :org_id) AS receipts,
      (SELECT COALESCE(SUM(inv.amount - COALESCE(paid.total, 0)), 0)
         FROM o2c_sales_invoices inv
         LEFT JOIN (
             SELECT sales_invoice_id, SUM(amount) AS total
               FROM o2c_collections
              WHERE organization_id = :org_id AND status = 'completed'
              GROUP BY sales_invoice_id
         ) paid ON paid.sales_invoice_id = inv.id
        WHERE inv.organization_id = :org_id
          AND inv.status <> 'cancelled'
          AND inv.approval_status = 'approved') AS outstanding_receivables,
      (SELECT COALESCE(SUM(inv.amount - COALESCE(paid.total, 0)), 0)
         FROM p2p_supplier_invoices inv
         LEFT JOIN (
             SELECT supplier_invoice_id, SUM(amount) AS total
               FROM p2p_payments
              WHERE organization_id = :org_id AND status = 'completed'
              GROUP BY supplier_invoice_id
         ) paid ON paid.supplier_invoice_id = inv.id
        WHERE inv.organization_id = :org_id
          AND inv.status <> 'cancelled'
          AND inv.approval_status = 'approved') AS outstanding_payables
    """
)


async def compute(session: AsyncSession, tenant_id: UUID) -> CashPositionSnapshot:
    row = (await session.execute(_COMPUTE_SQL, {"org_id": tenant_id})).one()
    return CashPositionSnapshot(
        expenses=_as_money(row.expenses),
        payments=_as_money(row.payments),
        collections=_as_money(row.collections),
        receipts=_as_money(row.receipts),
        outstanding_receivables=_as_money(row.outstanding_receivables),
        outstanding_payables=_as_money(row.outstanding_payables),
    )


def to_items(snapshot: CashPositionSnapshot) -> list[CashPositionItem]:
    return [
        CashPositionItem(
            account_name="Expenses (finance transactions)",
            account_type="outflow",
            balance=_money(snapshot.expenses),
        ),
        CashPositionItem(
            account_name="Supplier payments",
            account_type="outflow",
            balance=_money(snapshot.payments),
        ),
        CashPositionItem(
            account_name="Customer collections",
            account_type="inflow",
            balance=_money(snapshot.collections),
        ),
        CashPositionItem(
            account_name="Legacy receipts",
            account_type="inflow",
            balance=_money(snapshot.receipts),
        ),
        CashPositionItem(
            account_name="Net cash-basis position",
            account_type="net",
            balance=_money(snapshot.net),
        ),
    ]


def to_summary(snapshot: CashPositionSnapshot) -> DashboardSummary:
    return DashboardSummary(
        total_income=_money(snapshot.total_income),
        total_expenses=_money(snapshot.total_outflow),
        cash_in_hand=_money(snapshot.net),
        outstanding_receivables=_money(snapshot.outstanding_receivables),
        outstanding_payables=_money(snapshot.outstanding_payables),
    )
