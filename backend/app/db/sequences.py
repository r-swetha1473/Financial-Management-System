"""Organization-scoped document numbering.

Call increment_sequence inside the same transaction as the document insert.
Wired to purchase-request, purchase-order, goods-receipt, supplier-invoice, quotation, sales-order, delivery, and sales-invoice create.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_FLOOR_COLUMNS = {
    "p2p_purchase_requests": "request_number",
    "p2p_purchase_orders": "po_number",
    "p2p_goods_receipts": "grn_number",
    "p2p_supplier_invoices": "invoice_number",
    "o2c_quotations": "quote_number",
    "o2c_sales_orders": "order_number",
    "o2c_deliveries": "delivery_number",
    "o2c_sales_invoices": "invoice_number",
}


async def floor_year_sequence(
    session: AsyncSession,
    org_id: UUID,
    doc_type: str,
    *,
    table: str,
    number_column: str,
    pattern: str,
) -> None:
    """Raise current_number to at least the max matching document number for this tenant."""
    if _FLOOR_COLUMNS.get(table) != number_column:
        raise ValueError(f"Refusing to floor sequence on {table}.{number_column}")
    result = await session.execute(
        text(
            f"""
            SELECT COALESCE(MAX(CAST(split_part({number_column}, '-', 3) AS INTEGER)), 0)
            FROM {table}
            WHERE organization_id = :org_id
              AND {number_column} ~ :pattern
            """
        ),
        {"org_id": org_id, "pattern": pattern},
    )
    floor = int(result.scalar_one() or 0)
    await session.execute(
        text(
            """
            INSERT INTO document_sequences (organization_id, doc_type, current_number)
            VALUES (:org_id, :doc_type, :floor)
            ON CONFLICT (organization_id, doc_type)
            DO UPDATE SET current_number = GREATEST(
                document_sequences.current_number,
                EXCLUDED.current_number
            )
            """
        ),
        {"org_id": org_id, "doc_type": doc_type, "floor": floor},
    )


async def increment_sequence(session: AsyncSession, org_id: UUID, doc_type: str) -> int:
    """Lock the org/doc_type row, increment, and return the next number."""
    await session.execute(
        text(
            """
            INSERT INTO document_sequences (organization_id, doc_type, current_number)
            VALUES (:org_id, :doc_type, 0)
            ON CONFLICT (organization_id, doc_type) DO NOTHING
            """
        ),
        {"org_id": org_id, "doc_type": doc_type},
    )
    result = await session.execute(
        text(
            """
            SELECT current_number
            FROM document_sequences
            WHERE organization_id = :org_id AND doc_type = :doc_type
            FOR UPDATE
            """
        ),
        {"org_id": org_id, "doc_type": doc_type},
    )
    current = result.scalar_one()
    nxt = current + 1
    await session.execute(
        text(
            """
            UPDATE document_sequences
            SET current_number = :nxt
            WHERE organization_id = :org_id AND doc_type = :doc_type
            """
        ),
        {"nxt": nxt, "org_id": org_id, "doc_type": doc_type},
    )
    return nxt
