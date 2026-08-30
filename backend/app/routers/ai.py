import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.ai import AIRestockRequest
from app.models.user import User
from app.schemas.ai import AIRestockParseRequest, AIRestockRequestRead
from app.services.ai_service import confirm_restock_request, list_recent, parse_restock_message, reject_restock_request

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _serialize(request: AIRestockRequest) -> AIRestockRequestRead:
    data = AIRestockRequestRead.model_validate(request)
    if request.resolved_product is not None:
        data.resolved_product_name = request.resolved_product.name
        data.current_stock = request.resolved_product.stock_quantity
    return data


@router.post("/restock/parse", response_model=AIRestockRequestRead)
def parse_restock(payload: AIRestockParseRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> AIRestockRequestRead:
    request = parse_restock_message(db, admin, payload.message, payload.input_type)
    return _serialize(request)


@router.post("/restock/{request_id}/confirm", response_model=AIRestockRequestRead)
def confirm_restock(request_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> AIRestockRequestRead:
    request = confirm_restock_request(db, admin, request_id)
    return _serialize(request)


@router.post("/restock/{request_id}/reject", response_model=AIRestockRequestRead)
def reject_restock(request_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> AIRestockRequestRead:
    request = reject_restock_request(db, request_id)
    return _serialize(request)


@router.get("/restock/history", response_model=list[AIRestockRequestRead])
def restock_history(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[AIRestockRequestRead]:
    requests = list_recent(db, limit=50)
    return [_serialize(r) for r in requests]
