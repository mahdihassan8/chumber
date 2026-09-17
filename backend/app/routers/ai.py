import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.core.regions import get_current_region
from app.db.session import get_db
from app.models.ai import AIRestockRequest
from app.models.user import Region, User
from app.schemas.ai import AIRestockParseRequest, AIRestockRequestRead
from app.schemas.ai_product import AIProductDraftConfirm, AIProductDraftRead, AIProductDraftRequest
from app.services import ai_product_service
from app.services.ai_service import confirm_restock_request, list_recent, parse_restock_message, reject_restock_request

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _serialize(request: AIRestockRequest) -> AIRestockRequestRead:
    data = AIRestockRequestRead.model_validate(request)
    if request.resolved_product is not None:
        data.resolved_product_name = request.resolved_product.name
        data.current_stock = request.resolved_product.stock_quantity
    return data


@router.post("/restock/parse", response_model=AIRestockRequestRead)
def parse_restock(
    payload: AIRestockParseRequest,
    admin: User = Depends(require_admin),
    region: Region = Depends(get_current_region),
    db: Session = Depends(get_db),
) -> AIRestockRequestRead:
    request = parse_restock_message(db, admin, payload.message, payload.input_type, region)
    return _serialize(request)


@router.post("/restock/{request_id}/confirm", response_model=AIRestockRequestRead)
def confirm_restock(
    request_id: uuid.UUID,
    admin: User = Depends(require_admin),
    region: Region = Depends(get_current_region),
    db: Session = Depends(get_db),
) -> AIRestockRequestRead:
    request = confirm_restock_request(db, admin, request_id, region)
    return _serialize(request)


@router.post("/restock/{request_id}/reject", response_model=AIRestockRequestRead)
def reject_restock(request_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> AIRestockRequestRead:
    request = reject_restock_request(db, request_id)
    return _serialize(request)


@router.get("/restock/history", response_model=list[AIRestockRequestRead])
def restock_history(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[AIRestockRequestRead]:
    requests = list_recent(db, limit=50)
    return [_serialize(r) for r in requests]


# --- AI product creation ----------------------------------------------------
# Same propose-then-confirm contract as restocking above: /draft only ever
# writes an AIProductDraft, and /confirm is the single place a Product is
# created — via the ordinary product_service.create_product path.


@router.post("/products/draft", response_model=AIProductDraftRead)
def draft_product(
    payload: AIProductDraftRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AIProductDraftRead:
    draft = ai_product_service.create_draft(db, admin, payload.name)
    return AIProductDraftRead.model_validate(draft)


@router.post("/products/{draft_id}/confirm", response_model=AIProductDraftRead)
def confirm_product_draft(
    draft_id: uuid.UUID,
    payload: AIProductDraftConfirm,
    admin: User = Depends(require_admin),
    region: Region = Depends(get_current_region),
    db: Session = Depends(get_db),
) -> AIProductDraftRead:
    draft = ai_product_service.confirm_draft(db, admin, draft_id, payload, region)
    return AIProductDraftRead.model_validate(draft)


@router.post("/products/{draft_id}/retry-image", response_model=AIProductDraftRead)
def retry_product_draft_image(
    draft_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AIProductDraftRead:
    """Re-runs the image pipeline only. The admin's reviewed name, description
    and price are untouched."""
    draft = ai_product_service.retry_image(db, draft_id)
    return AIProductDraftRead.model_validate(draft)


@router.post("/products/{draft_id}/reject", response_model=AIProductDraftRead)
def reject_product_draft(
    draft_id: uuid.UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AIProductDraftRead:
    draft = ai_product_service.reject_draft(db, draft_id)
    return AIProductDraftRead.model_validate(draft)


@router.get("/products/history", response_model=list[AIProductDraftRead])
def product_draft_history(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[AIProductDraftRead]:
    return [AIProductDraftRead.model_validate(d) for d in ai_product_service.list_recent(db)]
