"""Read-only finance surfaces: accounts, transactions, cash-basis income, GST aggregation, notes."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.finance_accounts import OPERATING_CASH_NAME, FinanceAccountRepository
from app.repositories.finance_open import FinanceOpenRepository
from app.schemas.finance_open import (
    FinanceAccountOut,
    FinanceTransactionOut,
    GstSummaryOut,
    IncomeRecordOut,
    ReconciliationNoteOut,
)
from app.services import cash_position_service


def _money(value) -> Decimal:
    return Decimal(str(value if value is not None else 0))


async def list_accounts(session: AsyncSession, tenant_id: UUID):
    account = await FinanceAccountRepository(session, tenant_id).get_or_create_operating_cash()
    await session.commit()
    snapshot = await cash_position_service.compute(session, tenant_id)
    item = FinanceAccountOut(
        id=str(account.id),
        organization_id=str(account.organization_id),
        name=account.name,
        account_type=account.account_type,
        account_number=account.account_number,
        balance=snapshot.net,
        is_active=account.is_active,
        created_at=account.created_at,
    )
    return [item], 1


async def list_transactions(session, tenant_id, page, page_size, account_id: UUID | None, search: str):
    rows, total = await FinanceOpenRepository(session, tenant_id).list_transactions(page, page_size, account_id, search)
    items = [
        FinanceTransactionOut(
            id=str(row.id),
            organization_id=str(row.organization_id),
            account_id=str(row.account_id),
            account_name=name or OPERATING_CASH_NAME,
            transaction_type=row.transaction_type,
            amount=row.amount,
            reference_type=row.reference_type,
            reference_id=str(row.reference_id) if row.reference_id else None,
            description=row.description,
            transaction_date=row.transaction_date,
            reconciled=row.reconciled,
            created_at=row.created_at,
        )
        for row, name in rows
    ]
    return items, total


_INCOME_SQL = text(
    """
    SELECT * FROM (
      SELECT c.id,
             'collection'::text AS source_type,
             c.id AS source_id,
             '/o2c/collections/' || c.id AS source_route,
             COALESCE(cust.name, '') AS customer_name,
             COALESCE(inv.invoice_number, '') AS document_number,
             c.amount,
             0::numeric AS gst_amount,
             c.collection_date AS txn_date,
             c.status,
             c.created_at
        FROM o2c_collections c
        JOIN o2c_sales_invoices inv ON inv.id = c.sales_invoice_id
        LEFT JOIN customer_skg cust ON cust.id = inv.customer_id
       WHERE c.organization_id = :org_id
         AND c.status = 'completed'
      UNION ALL
      SELECT r.id,
             'receipt'::text,
             r.id,
             '/finance/receipts/' || r.id,
             COALESCE(cust.name, ''),
             COALESCE(inv.invoice_number, ''),
             r.receipt_amount,
             0::numeric,
             r.receipt_date,
             r.payment_mode,
             r.created_at
        FROM invoice_receipts r
        JOIN invoice_skg inv ON inv.id = r.invoice_id
        LEFT JOIN customer_skg cust ON cust.id = inv.customer_id
       WHERE r.organization_id = :org_id
    ) income
    ORDER BY txn_date DESC, created_at DESC
    LIMIT :limit OFFSET :offset
    """
)

_INCOME_COUNT_SQL = text(
    """
    SELECT (
      (SELECT COUNT(*) FROM o2c_collections WHERE organization_id = :org_id AND status = 'completed')
      + (SELECT COUNT(*) FROM invoice_receipts WHERE organization_id = :org_id)
    ) AS total
    """
)


async def list_income(session, tenant_id, page, page_size):
    total = int((await session.execute(_INCOME_COUNT_SQL, {"org_id": tenant_id})).scalar() or 0)
    rows = (await session.execute(
        _INCOME_SQL,
        {"org_id": tenant_id, "limit": page_size, "offset": (page - 1) * page_size},
    )).mappings().all()
    items = [
        IncomeRecordOut(
            id=str(row["id"]),
            source_type=row["source_type"],
            source_id=str(row["source_id"]),
            source_route=row["source_route"],
            customer_name=row["customer_name"] or "",
            document_number=row["document_number"] or "",
            amount=_money(row["amount"]),
            gst_amount=_money(row["gst_amount"]),
            date=row["txn_date"],
            status=row["status"] or "",
        )
        for row in rows
    ]
    return items, total


_GST_SQL = text(
    """
    SELECT
      (SELECT COALESCE(SUM(gst_amount), 0) FROM p2p_supplier_invoices
        WHERE organization_id = :org_id AND status <> 'cancelled'
          AND (CAST(:date_from AS date) IS NULL OR invoice_date >= CAST(:date_from AS date))
          AND (CAST(:date_to AS date) IS NULL OR invoice_date <= CAST(:date_to AS date))) AS supplier,
      (SELECT COALESCE(SUM(gst_amount), 0) FROM o2c_sales_invoices
        WHERE organization_id = :org_id AND status <> 'cancelled'
          AND (CAST(:date_from AS date) IS NULL OR invoice_date >= CAST(:date_from AS date))
          AND (CAST(:date_to AS date) IS NULL OR invoice_date <= CAST(:date_to AS date))) AS output_o2c,
      (SELECT COALESCE(SUM(gst_amount), 0) FROM invoice_skg
        WHERE organization_id = :org_id AND is_gst_invoice = TRUE
          AND (CAST(:date_from AS date) IS NULL OR invoice_raised_date >= CAST(:date_from AS date))
          AND (CAST(:date_to AS date) IS NULL OR invoice_raised_date <= CAST(:date_to AS date))) AS output_legacy
    """
)


async def gst_summary(session, tenant_id, date_from: date | None, date_to: date | None) -> GstSummaryOut:
    row = (await session.execute(_GST_SQL, {"org_id": tenant_id, "date_from": date_from, "date_to": date_to})).one()
    supplier = _money(row.supplier)
    output_o2c = _money(row.output_o2c)
    output_legacy = _money(row.output_legacy)
    output = output_o2c + output_legacy
    return GstSummaryOut(
        input_gst=supplier,
        output_gst=output,
        net=output - supplier,
        expenses=Decimal("0"),
        supplier=supplier,
        output_legacy=output_legacy,
        output_o2c=output_o2c,
        date_from=date_from,
        date_to=date_to,
    )


async def get_reconciliation_note(session, tenant_id) -> ReconciliationNoteOut:
    row = await FinanceOpenRepository(session, tenant_id).get_or_create_note()
    return ReconciliationNoteOut(organization_id=str(row.organization_id), note=row.note, updated_at=row.updated_at)


async def save_reconciliation_note(session, tenant_id, note: str) -> ReconciliationNoteOut:
    row = await FinanceOpenRepository(session, tenant_id).save_note(note)
    return ReconciliationNoteOut(organization_id=str(row.organization_id), note=row.note, updated_at=row.updated_at)
