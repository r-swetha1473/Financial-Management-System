"""Vendor application service. Tenant comes from CurrentUser only."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor
from app.repositories.vendors import VendorRepository
from app.schemas.vendor import VendorCreate, VendorOut


def _to_out(vendor: Vendor) -> VendorOut:
    gst = vendor.gst_number
    return VendorOut(
        id=str(vendor.id),
        organization_id=str(vendor.organization_id),
        name=vendor.name,
        address=vendor.address,
        phone=vendor.phone,
        email=vendor.email,
        poc_name=vendor.poc_name,
        poc_email=vendor.poc_email,
        gstin=gst,
        state=vendor.state,
        status=vendor.status,
        created_at=vendor.created_at,
    )


async def list_vendors(
    session: AsyncSession,
    tenant_id: UUID,
    page: int,
    page_size: int,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[VendorOut], int]:
    rows, total = await VendorRepository(session, tenant_id).list_page(
        page, page_size, status=status, search=search
    )
    return [_to_out(row) for row in rows], total


async def get_vendor(session: AsyncSession, tenant_id: UUID, vendor_id: UUID) -> VendorOut:
    vendor = await VendorRepository(session, tenant_id).get_by_id(vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found in this organization.",
        )
    return _to_out(vendor)


async def create_vendor(session: AsyncSession, tenant_id: UUID, payload: VendorCreate) -> VendorOut:
    vendor = await VendorRepository(session, tenant_id).create(
        name=payload.name.strip(),
        address=payload.address,
        phone=payload.phone,
        email=payload.email,
        poc_name=payload.poc_name,
        poc_email=payload.poc_email,
        gst_number=payload.gstin,
        state=payload.state,
        status=payload.status,
    )
    return _to_out(vendor)
