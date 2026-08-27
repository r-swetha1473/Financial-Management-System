"""Test-only bypass of the audit_logs append-only DELETE trigger.

Never import this from app/ or from request handlers. The GUC is
transaction-scoped (set_config third argument true).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def allow_audit_delete_for_tests(session: AsyncSession) -> None:
    await session.execute(text("SELECT set_config('app.allow_audit_delete', 'on', true)"))
