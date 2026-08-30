# Chumber

A small private marketplace: registered users (Customers and Admins) browse a limited product catalog, hold an internal balance, and check out. Admins get a private dashboard for user/product/order/balance management and an AI-powered restocking assistant (text + voice).

## Stack

- **Frontend**: React + TypeScript, Vite, React Router, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **Auth**: JWT (bcrypt password hashing, role-based authorization)
- **AI**: Anthropic Claude API (forced tool-use for structured restock extraction)
- **Voice**: browser Web Speech API (client-side transcription)
- **Tests**: Pytest
- **Containerization**: Docker Compose

## Quick start

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set ANTHROPIC_API_KEY if you want the AI restocking
# assistant to work (it degrades gracefully to a "not configured" message
# without it — everything else works fine).

docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (docs at `/docs`)
- Postgres: exposed on host port **5433** (mapped to avoid clashing with a local Postgres install), `chumber` and `chumber_test` databases

On first boot the backend seeds one bootstrap Admin account so you have a way in:

- **Username**: `admin`
- **Password**: `ChangeMe123!` (from `BOOTSTRAP_ADMIN_PASSWORD` in `.env` — change it there before first run in anything beyond local dev)

There is no public sign-up: all accounts (Customer or Admin) are created by an Admin from **Admin Dashboard → Users**.

## Running tests

```bash
docker compose up -d db
docker compose exec backend pytest -v
```

Tests run against a separate `chumber_test` database and each test rolls back in its own transaction, so they're safe to re-run.

## Project layout

```
backend/
  app/
    core/       # settings, JWT/bcrypt, auth dependencies
    db/         # SQLAlchemy base, session, bootstrap-admin seed
    models/     # SQLAlchemy models
    schemas/    # Pydantic request/response models
    routers/    # FastAPI routers (one per domain)
    services/   # business logic (checkout atomicity, AI parsing, etc.)
  alembic/      # migrations
  tests/        # pytest suite
frontend/
  src/
    api/        # typed fetch client, one module per domain
    context/    # Auth, Cart, Toast providers
    components/ # reusable UI (layout, product, cart, admin, ai, ...)
    pages/      # routed pages (customer + admin/)
    router/     # route tree, protected/admin route guards
```

## Notes

- The frontend never talks to the database directly — all reads/writes go through the FastAPI backend, which re-validates everything (quantities, stock, balance, roles) server-side.
- Checkout is atomic: product and user rows are row-locked, stock/balance are re-checked, and the balance deduction + stock decrement + order creation + cart clear all happen in one DB transaction.
- The AI assistant only ever *proposes* a restock; nothing is written to the database until the Admin explicitly confirms it in the UI.
