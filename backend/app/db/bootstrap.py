"""Apply additive SQL and seed demo authentication users."""

from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import DEMO_ORGANIZATION_ID, DEMO_ORGANIZATION_NAME, DEMO_ORGANIZATION_SLUG, DEMO_USERS
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.organization import Organization
from app.models.user import User

INIT_DIR = Path(__file__).resolve().parents[2] / "db" / "init"


def _statements(sql: str) -> list[str]:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    body = "\n".join(lines)
    statements: list[str] = []
    buf: list[str] = []
    in_dollar = False
    i = 0
    while i < len(body):
        if body.startswith("$$", i):
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        char = body[i]
        if char == ";" and not in_dollar:
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(char)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


async def _run_sql_file(filename: str) -> None:
    path = INIT_DIR / filename
    sql = path.read_text(encoding="utf-8")
    async with engine.begin() as connection:
        for statement in _statements(sql):
            await connection.execute(text(statement))


async def _schema_ready(session: AsyncSession) -> bool:
    result = await session.execute(text("SELECT to_regclass('public.organizations')"))
    return result.scalar() is not None


async def _seed_demo_auth(session: AsyncSession) -> None:
    result = await session.execute(select(Organization).where(Organization.slug == DEMO_ORGANIZATION_SLUG))
    organization = result.scalar_one_or_none()
    if organization is None:
        organization = Organization(
            id=DEMO_ORGANIZATION_ID,
            name=DEMO_ORGANIZATION_NAME,
            slug=DEMO_ORGANIZATION_SLUG,
            is_active=True,
        )
        session.add(organization)
        await session.flush()

    for spec in DEMO_USERS:
        existing = await session.get(User, spec["id"])
        if existing is not None:
            continue
        session.add(
            User(
                id=spec["id"],
                organization_id=organization.id,
                username=spec["username"],
                email=spec["email"],
                full_name=spec["full_name"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
                is_active=True,
            )
        )


async def bootstrap() -> None:
    async with SessionLocal() as session:
        ready = await _schema_ready(session)
    if not ready:
        await _run_sql_file("001_schema.sql")
    await _run_sql_file("002_constraints.sql")
    await _run_sql_file("003_document_sequences.sql")
    await _run_sql_file("004_status_checks.sql")
    await _run_sql_file("005_vendor_state.sql")
    await _run_sql_file("006_customer_gst_credit.sql")
    await _run_sql_file("007_sales_invoice_approval.sql")
    await _run_sql_file("008_users_username_unique.sql")
    await _run_sql_file("009_audit_logs_append_only.sql")
    async with SessionLocal() as session:
        await _seed_demo_auth(session)
        await session.commit()
