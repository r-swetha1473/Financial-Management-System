"""BFMS FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.db.bootstrap import bootstrap
from app.db.session import engine
import app.models  # noqa: F401 — register all ORM tables before first flush


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await bootstrap()
    yield
    await engine.dispose()


app = FastAPI(
    title="Business Financial Management System",
    description="Multi-tenant SaaS platform for P2P, O2C, and finance operations",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "bfms-api"}
