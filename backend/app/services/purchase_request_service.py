"""Purchase-request application service. Tenant and requested_by come from the session."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.audit import write_audit_log
from app.models.purchase_request import PurchaseRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.purchase_requests import PurchaseRequestRepository
from app.schemas.purchase_request import PurchaseRequestCreate, PurchaseRequestOut

_DECIDABLE = frozenset({"draft", "submitted"})


def _to_out(row: PurchaseRequest, vendor_name: str | None, requested_by_name: str | None) -> PurchaseRequestOut:
    return PurchaseRequestOut(
        id=str(row.id),
        organization_id=str(row.organization_id),
        vendor_id=str(row.vendor_id) if row.vendor_id else None,
        vendor_name=vendor_name or "",
        request_number=row.request_number,
        status=row.status,
        requested_by=str(row.requested_by) if row.requested_by else None,
        requested_by_name=requested_by_name or "",
        requested_date=row.requested_date,
        notes=row.notes,
        created_at=row.created_at,
    )


async def list_purchase_requests(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[PurchaseRequestOut], int]:
    rows, total = await PurchaseRequestRepository(session, tenant_id).list_page(page, page_size)
    return [_to_out(request, vendor_name, requested_by_name) for request, vendor_name, requested_by_name in rows], total


async def get_purchase_request(session: AsyncSession, tenant_id: UUID, request_id: UUID) -> PurchaseRequestOut:
    named = await PurchaseRequestRepository(session, tenant_id).get_by_id(request_id)
    if named is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase request not found in this organization.",
        )
    request, vendor_name, requested_by_name = named
    return _to_out(request, vendor_name, requested_by_name)


async def create_purchase_request(
    session: AsyncSession,
    tenant_id: UUID,
    requested_by: UUID,
    payload: PurchaseRequestCreate,
) -> PurchaseRequestOut:
    vendor_name: str | None = None
    if payload.vendor_id is not None:
        vendor = await session.get(Vendor, payload.vendor_id)
        if vendor is None or vendor.organization_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found in this organization.")
        vendor_name = vendor.name

    row = await PurchaseRequestRepository(session, tenant_id).create(
        vendor_id=payload.vendor_id,
        requested_by=requested_by,
        requested_date=payload.requested_date or date.today(),
        notes=payload.notes,
        status=payload.status,
    )
    user = await session.get(User, requested_by)
    return _to_out(row, vendor_name, user.full_name if user else None)


async def decide_purchase_request(
    session: AsyncSession,
    tenant_id: UUID,
    actor_id: UUID,
    request_id: UUID,
    decision: Literal["approved", "rejected"],
) -> PurchaseRequestOut:
    repo = PurchaseRequestRepository(session, tenant_id)
    request = await repo.get_for_update(request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase request not found in this organization.",
        )
    if request.status not in _DECIDABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Purchase request has already been {request.status}.",
        )

    previous = request.status
    request.status = decision
    action = "approve" if decision == "approved" else "reject"
    write_audit_log(
        session,
        organization_id=tenant_id,
        user_id=actor_id,
        action=action,
        entity_name="purchase_request",
        entity_id=request.id,
        old_values={"status": previous},
        new_values={"status": decision, "request_number": request.request_number},
    )
    await session.commit()
    await session.refresh(request)

    named = await repo.get_by_id(request.id)
    if named is None:
        return _to_out(request, None, None)
    row, vendor_name, requested_by_name = named
    return _to_out(row, vendor_name, requested_by_name)
