# LedgerFlow — Business Financial Management System

Multi-tenant SaaS platform for **P2P**, **O2C**, finance, GST, and existing operational records (expenses, invoices, bookings, receipts).

This is **not** a personal finance app and is **not** hard-coded to a single company. Each organization has isolated data. A demo tenant is used only for local development.

## Stack

- Frontend: Angular 20 (standalone), TypeScript, custom CSS, Chart.js
- Backend: FastAPI, Pydantic
- Database: PostgreSQL 16

## Quick start

### 1. Database

```bash
docker compose up -d postgres
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env   # or cp
uvicorn app.main:app --reload --app-dir . --port 8000
```

API docs: http://localhost:8000/api/docs

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

App: http://localhost:4200

Demo login (development tenant only):

- Email: `admin@demo-business.com`
- Password: `admin123`

If the API is not running, the frontend still signs in using the same contract via a development fallback (`environment.useDevSeed`).

## Phase 1 scope

- Design system and application shell
- Authentication (JWT-ready)
- Dashboard
- Organization context in session
- First-class P2P and O2C navigation
- FastAPI skeleton + PostgreSQL schema foundation

Operational CRUD for P2P/O2C/finance follows in Phases 2–5.
