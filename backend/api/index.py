"""Vercel Python entry. Re-exports the existing FastAPI app. Local dev still uses uvicorn app.main:app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

__all__ = ["app"]
