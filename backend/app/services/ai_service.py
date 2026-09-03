import difflib
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import AIRequestInputType, AIRequestStatus, AIRestockRequest
from app.models.product import Product
from app.models.user import User
from app.repositories.ai_restock_repository import AIRestockRequestRepository
from app.repositories.product_repository import ProductRepository
from app.services.product_service import restock_product

GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_TIMEOUT_MS = 30_000

SYSTEM_PROMPT = (
    "You extract structured restocking instructions from a marketplace admin's message. "
    "Always respond with your best interpretation of the product name and the quantity to add. "
    "Never invent a quantity if none is given; if unclear, use 0."
)


class _RestockAction(BaseModel):
    action: Literal["restock"] = "restock"
    product_name: str
    quantity: int


def _find_matching_product(db: Session, product_name: str) -> Product | None:
    products = ProductRepository(db).list_all()
    if not products:
        return None

    normalized = product_name.strip().lower()
    for product in products:
        if product.name.strip().lower() == normalized:
            return product

    names = [p.name.lower() for p in products]
    matches = difflib.get_close_matches(normalized, names, n=1, cutoff=0.5)
    if matches:
        for product in products:
            if product.name.lower() == matches[0]:
                return product

    for product in products:
        if normalized in product.name.lower() or product.name.lower() in normalized:
            return product

    return None


def parse_restock_message(db: Session, admin: User, message: str, input_type: AIRequestInputType) -> AIRestockRequest:
    repo = AIRestockRequestRepository(db)

    if not settings.gemini_api_key:
        request = AIRestockRequest(
            admin_id=admin.id,
            raw_input=message,
            input_type=input_type,
            status=AIRequestStatus.FAILED,
            error_message="AI assistant is not configured (missing GEMINI_API_KEY).",
        )
        repo.add(request)
        db.commit()
        db.refresh(request)
        return request

    client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_RestockAction,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        # error_message is String(500) - a real API error (e.g. a verbose
        # quota-exceeded message) can be much longer than that, which would
        # otherwise turn this graceful-failure path into an unhandled DB
        # error (StringDataRightTruncation) instead of a clean FAILED status.
        request = AIRestockRequest(
            admin_id=admin.id,
            raw_input=message,
            input_type=input_type,
            status=AIRequestStatus.FAILED,
            error_message=f"AI request failed: {exc}"[:500],
        )
        repo.add(request)
        db.commit()
        db.refresh(request)
        return request

    parsed = response.parsed
    if parsed is None:
        request = AIRestockRequest(
            admin_id=admin.id,
            raw_input=message,
            input_type=input_type,
            status=AIRequestStatus.FAILED,
            error_message="Could not understand the request.",
        )
        repo.add(request)
        db.commit()
        db.refresh(request)
        return request

    product_name = parsed.product_name.strip()
    quantity = int(parsed.quantity or 0)
    matched_product = _find_matching_product(db, product_name) if product_name else None

    request = AIRestockRequest(
        admin_id=admin.id,
        raw_input=message,
        input_type=input_type,
        parsed_action=parsed.action,
        parsed_product_name=product_name,
        parsed_quantity=quantity,
        resolved_product_id=matched_product.id if matched_product else None,
        status=AIRequestStatus.PENDING,
    )
    repo.add(request)
    db.commit()
    db.refresh(request)
    return request


def confirm_restock_request(db: Session, admin: User, request_id: uuid.UUID) -> AIRestockRequest:
    request = AIRestockRequestRepository(db).get_by_id(request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restock request not found")
    if request.status != AIRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is not pending")
    if request.resolved_product_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No matching product was found for this request")
    if not request.parsed_quantity or request.parsed_quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be a positive number")
    if request.parsed_quantity > 100000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity is unreasonably large")

    product = ProductRepository(db).get_by_id(request.resolved_product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product no longer exists")

    restock_product(db, product, request.parsed_quantity)

    request.status = AIRequestStatus.CONFIRMED
    request.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(request)
    return request


def reject_restock_request(db: Session, request_id: uuid.UUID) -> AIRestockRequest:
    request = AIRestockRequestRepository(db).get_by_id(request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restock request not found")
    if request.status != AIRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is not pending")

    request.status = AIRequestStatus.REJECTED
    db.commit()
    db.refresh(request)
    return request


def list_recent(db: Session, limit: int = 50) -> list[AIRestockRequest]:
    return AIRestockRequestRepository(db).list_recent(limit)
