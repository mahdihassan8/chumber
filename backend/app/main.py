import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.seed import seed_bootstrap_admin
from app.db.session import SessionLocal
from app.routers import admin, ai, auth, balance, cart, giveaway, orders, products, profile, users


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db = SessionLocal()
    try:
        seed_bootstrap_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Chumber API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(__file__).resolve().parent / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(balance.router)
app.include_router(profile.router)
app.include_router(ai.router)
app.include_router(admin.router)
app.include_router(giveaway.router)


def _json_safe(value: Any) -> Any:
    """Recursively replace non-finite floats (inf/-inf/nan) with their string
    form. Only relevant to error responses: request bodies can legally
    contain these as JSON literals (Infinity/NaN are non-standard but
    accepted by Python's json parser), and when a field rejects one via
    allow_inf_nan=False, FastAPI's default validation handler echoes the
    rejected value back in the response — which then fails to serialize at
    all, since Starlette's JSONResponse uses allow_nan=False. Without this,
    that's an unhandled 500 instead of the intended clean 422.
    """
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": _json_safe(exc.errors())})


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
