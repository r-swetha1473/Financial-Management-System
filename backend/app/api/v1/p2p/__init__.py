"""P2P API routes."""

from fastapi import APIRouter

from app.api.v1.p2p import (
    goods_receipts,
    payables,
    payments,
    purchase_orders,
    purchase_requests,
    supplier_invoices,
    vendors,
)

router = APIRouter(prefix="/p2p")
router.include_router(vendors.router)
router.include_router(purchase_requests.router)
router.include_router(purchase_orders.router)
router.include_router(goods_receipts.router)
router.include_router(supplier_invoices.router)
router.include_router(payments.router)
router.include_router(payables.router)
