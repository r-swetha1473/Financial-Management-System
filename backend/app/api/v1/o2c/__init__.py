"""O2C API routes."""

from fastapi import APIRouter

from app.api.v1.o2c import collections, customers, deliveries, quotations, receivables, sales_invoices, sales_orders

router = APIRouter(prefix="/o2c")
router.include_router(customers.router)
router.include_router(quotations.router)
router.include_router(sales_orders.router)
router.include_router(deliveries.router)
router.include_router(sales_invoices.router)
router.include_router(collections.router)
router.include_router(receivables.router)
