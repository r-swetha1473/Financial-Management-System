"""Tenant-scoped dashboard recent rows and cash-basis income/expense trend."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import (
    DashboardTrendPoint,
    RecentExpenseRow,
    RecentInvoiceRow,
    RecentReceiptRow,
)

RECENT_LIMIT = 8
_TREND_PERIODS = frozenset({"daily", "weekly", "monthly"})


def _money(value: object) -> str:
    return format(Decimal(str(value if value is not None else 0)).quantize(Decimal("0.0001")), "f")


def _text(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text_value = str(value).strip()
    return text_value or fallback


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return date(year, month, day)


def _trend_window(period: str, today: date) -> tuple[str, date, date, str]:
    if period == "daily":
        return "day", today - timedelta(days=6), today, "1 day"
    if period == "weekly":
        week_start = today - timedelta(days=today.weekday())
        return "week", week_start - timedelta(weeks=3), week_start, "7 days"
    month_start = today.replace(day=1)
    return "month", _add_months(month_start, -5), month_start, "1 month"


def _trend_label(period: str, bucket: date) -> str:
    if period == "daily":
        return bucket.strftime("%d %b")
    if period == "weekly":
        return f"Week of {bucket.isoformat()}"
    return bucket.strftime("%b %Y")


_EXPENSES_SQL = text(
    """
    SELECT t.id,
           v.name AS vendor_name,
           t.amount,
           t.transaction_date,
           t.reconciled
      FROM finance_transactions t
      LEFT JOIN vendors v
        ON v.id = t.reference_id
       AND v.organization_id = t.organization_id
     WHERE t.organization_id = :org_id
       AND t.transaction_type = 'debit'
       AND t.reference_type = 'expense'
     ORDER BY t.transaction_date DESC, t.created_at DESC
     LIMIT :limit
    """
)

_INVOICES_SQL = text(
    """
    SELECT * FROM (
      SELECT inv.id,
             inv.invoice_number,
             cust.name AS customer_name,
             inv.amount,
             inv.invoice_date AS raised_date,
             inv.status,
             inv.created_at
        FROM o2c_sales_invoices inv
        LEFT JOIN customer_skg cust ON cust.id = inv.customer_id
       WHERE inv.organization_id = :org_id
      UNION ALL
      SELECT inv.id,
             inv.invoice_number,
             cust.name,
             inv.invoice_amount,
             inv.invoice_raised_date,
             'raised',
             inv.created_at
        FROM invoice_skg inv
        LEFT JOIN customer_skg cust ON cust.id = inv.customer_id
       WHERE inv.organization_id = :org_id
    ) invoices
    ORDER BY raised_date DESC, created_at DESC
    LIMIT :limit
    """
)

_RECEIPTS_SQL = text(
    """
    SELECT * FROM (
      SELECT c.id,
             inv.invoice_number,
             c.amount,
             c.collection_date AS receipt_date,
             c.payment_mode,
             c.created_at
        FROM o2c_collections c
        JOIN o2c_sales_invoices inv ON inv.id = c.sales_invoice_id
       WHERE c.organization_id = :org_id
         AND c.status = 'completed'
      UNION ALL
      SELECT r.id,
             inv.invoice_number,
             r.receipt_amount,
             r.receipt_date,
             r.payment_mode,
             r.created_at
        FROM invoice_receipts r
        JOIN invoice_skg inv ON inv.id = r.invoice_id
       WHERE r.organization_id = :org_id
    ) receipts
    ORDER BY receipt_date DESC, created_at DESC
    LIMIT :limit
    """
)


async def list_recent_expenses(session: AsyncSession, tenant_id: UUID) -> list[RecentExpenseRow]:
    rows = (await session.execute(_EXPENSES_SQL, {"org_id": tenant_id, "limit": RECENT_LIMIT})).mappings().all()
    return [
        RecentExpenseRow(
            id=str(row["id"]),
            vendor=_text(row["vendor_name"]),
            category="—",
            amount=_money(row["amount"]),
            expense_date=row["transaction_date"].isoformat(),
            status="reconciled" if row["reconciled"] else "posted",
        )
        for row in rows
    ]


async def list_recent_invoices(session: AsyncSession, tenant_id: UUID) -> list[RecentInvoiceRow]:
    rows = (await session.execute(_INVOICES_SQL, {"org_id": tenant_id, "limit": RECENT_LIMIT})).mappings().all()
    return [
        RecentInvoiceRow(
            id=str(row["id"]),
            invoice_number=_text(row["invoice_number"], ""),
            customer=_text(row["customer_name"]),
            amount=_money(row["amount"]),
            raised_date=row["raised_date"].isoformat(),
            status=_text(row["status"], "raised"),
        )
        for row in rows
    ]


async def list_recent_receipts(session: AsyncSession, tenant_id: UUID) -> list[RecentReceiptRow]:
    rows = (await session.execute(_RECEIPTS_SQL, {"org_id": tenant_id, "limit": RECENT_LIMIT})).mappings().all()
    return [
        RecentReceiptRow(
            id=str(row["id"]),
            invoice_number=_text(row["invoice_number"], ""),
            amount=_money(row["amount"]),
            receipt_date=row["receipt_date"].isoformat(),
            payment_mode=_text(row["payment_mode"], ""),
        )
        for row in rows
    ]


_TREND_SQL = text(
    """
    WITH inflow AS (
      SELECT date_trunc(CAST(:field AS text), collection_date)::date AS bucket, SUM(amount) AS amount
        FROM o2c_collections
       WHERE organization_id = :org_id AND status = 'completed'
       GROUP BY 1
      UNION ALL
      SELECT date_trunc(CAST(:field AS text), receipt_date)::date, SUM(receipt_amount)
        FROM invoice_receipts
       WHERE organization_id = :org_id
       GROUP BY 1
    ),
    inflow_sum AS (
      SELECT bucket, SUM(amount) AS amount FROM inflow GROUP BY bucket
    ),
    outflow AS (
      SELECT date_trunc(CAST(:field AS text), transaction_date)::date AS bucket, SUM(amount) AS amount
        FROM finance_transactions
       WHERE organization_id = :org_id AND transaction_type = 'debit'
       GROUP BY 1
      UNION ALL
      SELECT date_trunc(CAST(:field AS text), payment_date)::date, SUM(amount)
        FROM p2p_payments
       WHERE organization_id = :org_id AND status = 'completed'
       GROUP BY 1
    ),
    outflow_sum AS (
      SELECT bucket, SUM(amount) AS amount FROM outflow GROUP BY bucket
    )
    SELECT COALESCE(i.bucket, o.bucket) AS bucket,
           COALESCE(i.amount, 0) AS income,
           COALESCE(o.amount, 0) AS expenses
      FROM inflow_sum i
      FULL OUTER JOIN outflow_sum o ON o.bucket = i.bucket
     WHERE COALESCE(i.bucket, o.bucket) BETWEEN CAST(:start_d AS date) AND CAST(:end_d AS date)
    """
)


def _bucket_dates(period: str, start_d: date, end_d: date) -> list[date]:
    buckets: list[date] = []
    cursor = start_d
    while cursor <= end_d:
        buckets.append(cursor)
        if period == "daily":
            cursor += timedelta(days=1)
        elif period == "weekly":
            cursor += timedelta(weeks=1)
        else:
            cursor = _add_months(cursor, 1)
    return buckets


async def list_income_expense_trend(
    session: AsyncSession,
    tenant_id: UUID,
    period: str,
    today: date | None = None,
) -> list[DashboardTrendPoint]:
    if period not in _TREND_PERIODS:
        period = "monthly"
    field, start_d, end_d, _step = _trend_window(period, today or date.today())
    rows = (
        await session.execute(
            _TREND_SQL,
            {
                "org_id": tenant_id,
                "field": field,
                "start_d": start_d,
                "end_d": end_d,
            },
        )
    ).mappings().all()
    by_bucket = {row["bucket"]: row for row in rows}
    return [
        DashboardTrendPoint(
            label=_trend_label(period, bucket),
            income=_money(by_bucket[bucket]["income"] if bucket in by_bucket else 0),
            expenses=_money(by_bucket[bucket]["expenses"] if bucket in by_bucket else 0),
        )
        for bucket in _bucket_dates(period, start_d, end_d)
    ]
