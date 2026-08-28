"""Live report aggregations. Purchase/Sales/Payables/Receivables/Cash Flow/GST/P&L."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.reports import ReportColumn, ReportKpi, ReportViewOut
from app.services import cash_position_service, finance_open_service


def _m(value) -> str:
    return format(Decimal(str(value if value is not None else 0)).quantize(Decimal("0.0001")), "f")


async def build(session: AsyncSession, tenant_id: UUID, key: str) -> ReportViewOut:
    mapping = {
        "p2p": _purchase,
        "purchase": _purchase,
        "o2c": _sales,
        "sales": _sales,
        "payables": _payables,
        "receivables": _receivables,
        "gst": _gst,
        "cash-flow": _cash_flow,
        "financial-summary": _pnl,
        "pnl": _pnl,
    }
    builder = mapping.get(key)
    if builder is None:
        return ReportViewOut(
            key=key,
            title="Report",
            subtitle="This report is not in the live set.",
            note="Only Purchase, Sales, Payables, Receivables, Cash Flow, GST Summary, and P&L are backed by the API.",
            kpis=[],
            columns=[],
            rows=[],
        )
    return await builder(session, tenant_id)


async def _purchase(session, tenant_id) -> ReportViewOut:
    rows = (
        await session.execute(
            text(
                """
                SELECT 'Purchase order' AS document, po.po_number AS number, v.name AS party, po.total_amount AS amount, po.status
                  FROM p2p_purchase_orders po
                  JOIN vendors v ON v.id = po.vendor_id
                 WHERE po.organization_id = :org
                UNION ALL
                SELECT 'Supplier invoice', si.invoice_number, v.name, si.amount, si.status
                  FROM p2p_supplier_invoices si
                  JOIN vendors v ON v.id = si.vendor_id
                 WHERE si.organization_id = :org
                ORDER BY 2
                """
            ),
            {"org": tenant_id},
        )
    ).mappings().all()
    po_count = (await session.execute(text("SELECT COUNT(*) FROM p2p_purchase_orders WHERE organization_id=:org"), {"org": tenant_id})).scalar() or 0
    inv_total = (await session.execute(text("SELECT COALESCE(SUM(amount),0) FROM p2p_supplier_invoices WHERE organization_id=:org AND status<>'cancelled'"), {"org": tenant_id})).scalar()
    return ReportViewOut(
        key="p2p",
        title="Purchase report",
        subtitle="Purchase orders and supplier invoices in this organization.",
        note="",
        kpis=[
            ReportKpi(label="Purchase orders", value=str(int(po_count)), format="text"),
            ReportKpi(label="Supplier invoice total", value=_m(inv_total), tone="payable"),
        ],
        columns=[
            ReportColumn(key="document", label="Document"),
            ReportColumn(key="number", label="Number"),
            ReportColumn(key="party", label="Vendor"),
            ReportColumn(key="amount", label="Amount", type="money"),
            ReportColumn(key="status", label="Status", type="status"),
        ],
        rows=[{k: ( _m(r[k]) if k == "amount" else str(r[k] or "") ) for k in ("document", "number", "party", "amount", "status")} for r in rows],
    )


async def _sales(session, tenant_id) -> ReportViewOut:
    rows = (
        await session.execute(
            text(
                """
                SELECT 'Subscribed plan' AS document, q.quote_number AS number, c.name AS party, q.total_amount AS amount, q.status
                  FROM o2c_quotations q
                  JOIN customer_skg c ON c.id = q.customer_id
                 WHERE q.organization_id = :org
                UNION ALL
                SELECT 'Sales invoice', si.invoice_number, c.name, si.amount, si.status
                  FROM o2c_sales_invoices si
                  JOIN customer_skg c ON c.id = si.customer_id
                 WHERE si.organization_id = :org
                ORDER BY 2
                """
            ),
            {"org": tenant_id},
        )
    ).mappings().all()
    plan_count = (await session.execute(text("SELECT COUNT(*) FROM o2c_quotations WHERE organization_id=:org"), {"org": tenant_id})).scalar() or 0
    inv_total = (await session.execute(text("SELECT COALESCE(SUM(amount),0) FROM o2c_sales_invoices WHERE organization_id=:org AND status<>'cancelled'"), {"org": tenant_id})).scalar()
    return ReportViewOut(
        key="o2c",
        title="Sales report",
        subtitle="Subscribed plans and sales invoices in this organization.",
        note="",
        kpis=[
            ReportKpi(label="Subscribed plans", value=str(int(plan_count)), format="text"),
            ReportKpi(label="Sales invoice total", value=_m(inv_total), tone="income"),
        ],
        columns=[
            ReportColumn(key="document", label="Document"),
            ReportColumn(key="number", label="Number"),
            ReportColumn(key="party", label="Customer"),
            ReportColumn(key="amount", label="Amount", type="money"),
            ReportColumn(key="status", label="Status", type="status"),
        ],
        rows=[{k: (_m(r[k]) if k == "amount" else str(r[k] or "")) for k in ("document", "number", "party", "amount", "status")} for r in rows],
    )


async def _payables(session, tenant_id) -> ReportViewOut:
    rows = (
        await session.execute(
            text(
                """
                SELECT COALESCE(si.invoice_number, '') AS invoice_number,
                       COALESCE(v.name, '') AS vendor_name,
                       p.amount, p.outstanding, p.status
                  FROM payables p
                  LEFT JOIN vendors v ON v.id = p.vendor_id
                  LEFT JOIN p2p_supplier_invoices si
                    ON si.id = p.source_id AND p.source_type = 'supplier_invoice'
                 WHERE p.organization_id = :org
                 ORDER BY p.created_at DESC
                """
            ),
            {"org": tenant_id},
        )
    ).mappings().all()
    outstanding = (await session.execute(text("SELECT COALESCE(SUM(outstanding),0) FROM payables WHERE organization_id=:org"), {"org": tenant_id})).scalar()
    return ReportViewOut(
        key="payables",
        title="Payables report",
        subtitle="Open supplier balances.",
        note="Outstanding is the live payable cache; payments reduce it.",
        kpis=[ReportKpi(label="Outstanding payables", value=_m(outstanding), tone="payable")],
        columns=[
            ReportColumn(key="invoiceNumber", label="Invoice"),
            ReportColumn(key="vendorName", label="Vendor"),
            ReportColumn(key="amount", label="Amount", type="money"),
            ReportColumn(key="outstanding", label="Outstanding", type="money"),
            ReportColumn(key="status", label="Status", type="status"),
        ],
        rows=[
            {
                "invoiceNumber": r["invoice_number"] or "",
                "vendorName": r["vendor_name"] or "",
                "amount": _m(r["amount"]),
                "outstanding": _m(r["outstanding"]),
                "status": r["status"] or "",
            }
            for r in rows
        ],
    )


async def _receivables(session, tenant_id) -> ReportViewOut:
    rows = (
        await session.execute(
            text(
                """
                SELECT COALESCE(si.invoice_number, '') AS invoice_number,
                       COALESCE(c.name, '') AS customer_name,
                       r.amount, r.outstanding, r.status
                  FROM receivables r
                  LEFT JOIN customer_skg c ON c.id = r.customer_id
                  LEFT JOIN o2c_sales_invoices si
                    ON si.id = r.source_id AND r.source_type = 'sales_invoice'
                 WHERE r.organization_id = :org
                 ORDER BY r.created_at DESC
                """
            ),
            {"org": tenant_id},
        )
    ).mappings().all()
    outstanding = (await session.execute(text("SELECT COALESCE(SUM(outstanding),0) FROM receivables WHERE organization_id=:org"), {"org": tenant_id})).scalar()
    return ReportViewOut(
        key="receivables",
        title="Receivables report",
        subtitle="Open customer balances.",
        note="",
        kpis=[ReportKpi(label="Outstanding receivables", value=_m(outstanding), tone="receivable")],
        columns=[
            ReportColumn(key="invoiceNumber", label="Invoice"),
            ReportColumn(key="customerName", label="Customer"),
            ReportColumn(key="amount", label="Amount", type="money"),
            ReportColumn(key="outstanding", label="Outstanding", type="money"),
            ReportColumn(key="status", label="Status", type="status"),
        ],
        rows=[
            {
                "invoiceNumber": r["invoice_number"] or "",
                "customerName": r["customer_name"] or "",
                "amount": _m(r["amount"]),
                "outstanding": _m(r["outstanding"]),
                "status": r["status"] or "",
            }
            for r in rows
        ],
    )


async def _gst(session, tenant_id) -> ReportViewOut:
    summary = await finance_open_service.gst_summary(session, tenant_id, None, None)
    return ReportViewOut(
        key="gst",
        title="GST summary",
        subtitle="Stored gst_amount on invoices. No tax calculation.",
        note="Single flat gst_amount. No CGST/SGST/IGST split. Expense GST is not stored.",
        kpis=[
            ReportKpi(label="Input GST", value=_m(summary.supplier), tone="payable"),
            ReportKpi(label="Output GST", value=_m(summary.output_gst), tone="income"),
            ReportKpi(label="Net (output − input)", value=_m(summary.net), tone="cash"),
        ],
        columns=[
            ReportColumn(key="source", label="Source"),
            ReportColumn(key="kind", label="Kind"),
            ReportColumn(key="gstAmount", label="GST amount", type="money"),
        ],
        rows=[
            {"source": "P2P supplier invoices", "kind": "input", "gstAmount": _m(summary.supplier)},
            {"source": "O2C sales invoices", "kind": "output", "gstAmount": _m(summary.output_o2c)},
            {"source": "Legacy booking invoices", "kind": "output", "gstAmount": _m(summary.output_legacy)},
        ],
    )


async def _cash_flow(session, tenant_id) -> ReportViewOut:
    snapshot = await cash_position_service.compute(session, tenant_id)
    return ReportViewOut(
        key="cash-flow",
        title="Cash flow",
        subtitle="Cash-basis movement from CashPositionService. No opening bank balance.",
        note="Collections + receipts − expenses − payments.",
        kpis=[
            ReportKpi(label="Total income", value=_m(snapshot.total_income), tone="income"),
            ReportKpi(label="Total outflow", value=_m(snapshot.total_outflow), tone="expense"),
            ReportKpi(label="Net cash movement", value=_m(snapshot.net), tone="cash"),
        ],
        columns=[
            ReportColumn(key="source", label="Source"),
            ReportColumn(key="direction", label="Direction"),
            ReportColumn(key="amount", label="Amount", type="money"),
        ],
        rows=[
            {"source": "Customer collections", "direction": "inflow", "amount": _m(snapshot.collections)},
            {"source": "Legacy receipts", "direction": "inflow", "amount": _m(snapshot.receipts)},
            {"source": "Expenses (finance transactions)", "direction": "outflow", "amount": _m(snapshot.expenses)},
            {"source": "Supplier payments", "direction": "outflow", "amount": _m(snapshot.payments)},
        ],
    )


async def _pnl(session, tenant_id) -> ReportViewOut:
    snapshot = await cash_position_service.compute(session, tenant_id)
    return ReportViewOut(
        key="financial-summary",
        title="P&L (cash-basis)",
        subtitle="Not an accrual P&L. Same formula as dashboard net cash movement.",
        note="Income = collections + receipts. Expenses = finance_transactions debit + completed payments.",
        kpis=[
            ReportKpi(label="Income", value=_m(snapshot.total_income), tone="income"),
            ReportKpi(label="Expenses", value=_m(snapshot.total_outflow), tone="expense"),
            ReportKpi(label="Net", value=_m(snapshot.net), tone="cash"),
        ],
        columns=[
            ReportColumn(key="metric", label="Metric"),
            ReportColumn(key="amount", label="Amount", type="money"),
        ],
        rows=[
            {"metric": "Income (cash)", "amount": _m(snapshot.total_income)},
            {"metric": "Expenses (cash)", "amount": _m(snapshot.total_outflow)},
            {"metric": "Net", "amount": _m(snapshot.net)},
            {"metric": "Outstanding receivables", "amount": _m(snapshot.outstanding_receivables)},
            {"metric": "Outstanding payables", "amount": _m(snapshot.outstanding_payables)},
        ],
    )
