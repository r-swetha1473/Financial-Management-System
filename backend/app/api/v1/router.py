"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, catalog, dashboard, documents, legacy, organizations, reference_data, reports
from app.api.v1.admin import router as admin_router
from app.api.v1.finance import router as finance_router
from app.api.v1.o2c import router as o2c_router
from app.api.v1.p2p import router as p2p_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(organizations.router)
api_router.include_router(documents.router)
api_router.include_router(catalog.products_router)
api_router.include_router(catalog.categories_router)
api_router.include_router(catalog.subcategories_router)
api_router.include_router(catalog.offerings_router)
api_router.include_router(legacy.bookings_router)
api_router.include_router(legacy.invoices_router)
api_router.include_router(legacy.receipts_router)
api_router.include_router(reference_data.router)
api_router.include_router(reports.router)
api_router.include_router(p2p_router)
api_router.include_router(o2c_router)
api_router.include_router(finance_router)
api_router.include_router(admin_router)

# Phase 2+ module routers (registered as implemented):
# master_data, reports, administration
