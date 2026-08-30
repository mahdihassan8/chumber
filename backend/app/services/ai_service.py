import difflib
import uuid
from datetime import datetime, timezone

from anthropic import Anthropic
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import AIRequestInputType, AIRequestStatus, AIRestockRequest
from app.models.product import Product
from app.models.user import User
from app.repositories.ai_restock_repository import AIRestockRequestRepository
from app.repositories.product_repository import ProductRepository
from app.services.product_service import restock_product

RESTOCK_TOOL = {
    "name": "extract_restock_action",
    "description": "Extract a structured restocking action from an admin's natural language request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["restock"], "description": "The action being requested."},
            "product_name": {"type": "string", "description": "The name of the product to restock, as mentioned by the admin."},
            "quantity": {"type": "integer", "description": "The number of units to add to stock."},
        },
        "required": ["action", "product_name", "quantity"],
    },
}

SYSTEM_PROMPT = (
    "You extract structured restocking instructions from a marketplace admin's message. "
    "Always call the extract_restock_action tool with your best interpretation of the product name "
    "and the quantity to add. Never invent a quantity if none is given; if unclear, use 0."
)


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

    if not settings.anthropic_api_key:
        request = AIRestockRequest(
            admin_id=admin.id,
            raw_input=message,
            input_type=input_type,
            status=AIRequestStatus.FAILED,
            error_message="AI assistant is not configured (missing ANTHROPIC_API_KEY).",
        )
        repo.add(request)
        db.commit()
        db.refresh(request)
        return request

    client = Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            tools=[RESTOCK_TOOL],
            tool_choice={"type": "tool", "name": "extract_restock_action"},
            messages=[{"role": "user", "content": message}],
        )
    except Exception as exc:  # noqa: BLE001
        request = AIRestockRequest(
            admin_id=admin.id,
            raw_input=message,
            input_type=input_type,
            status=AIRequestStatus.FAILED,
            error_message=f"AI request failed: {exc}",
        )
        repo.add(request)
        db.commit()
        db.refresh(request)
        return request

    tool_use_block = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use_block is None:
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

    parsed = tool_use_block.input
    product_name = str(parsed.get("product_name", "")).strip()
    quantity = int(parsed.get("quantity", 0) or 0)
    matched_product = _find_matching_product(db, product_name) if product_name else None

    request = AIRestockRequest(
        admin_id=admin.id,
        raw_input=message,
        input_type=input_type,
        parsed_action=str(parsed.get("action", "restock")),
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
