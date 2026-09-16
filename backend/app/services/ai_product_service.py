"""AI-assisted product creation: research -> image -> admin review -> create.

Mirrors the restock assistant's contract deliberately (services/ai_service.py):
the AI only ever *proposes*. A draft row is written, the admin sees exactly
what was found, and nothing becomes a Product until confirm_draft runs the
ordinary product_service.create_product path.

Model selection is kept local to this module rather than imported from
ai_service, because that module's model list differs between the main branch
and the production hardening branch; duplicating three strings is cheaper than
a service that only imports cleanly on one of them.
"""

import io
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import AIRequestStatus
from app.models.ai_product_draft import AIProductDraft
from app.models.user import Region, User
from app.repositories.ai_product_draft_repository import AIProductDraftRepository
from app.schemas.ai_product import AIProductDraftConfirm
from app.schemas.product import ProductCreate
from app.services import product_service
from app.services.image_fetch_service import fetch_image
from app.services.product_image_service import save_image

# Each model carries its own free-tier daily budget, so an exhausted one does
# not mean an exhausted key — fall through instead of failing the admin.
TEXT_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest")
IMAGE_MODELS = ("gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3-pro-image")
TIMEOUT_MS = 90_000
MAX_IMAGE_DIMENSION = 1024

RESEARCH_PROMPT = """You are helping an admin add a product to a small private marketplace.

Search the web for the product named below and reply with ONLY a JSON object
(no prose, no code fence) with exactly these keys:

  "product_name":   the canonical retail name
  "description":    one or two factual sentences about the product
  "image_url":      a direct link to a product photo (must end in .jpg/.jpeg/.png/.webp
                    and be a real image file, not an HTML page)
  "source_title":   the site or page the photo came from
  "suggested_price_iqd": a number, the approximate retail price in Iraqi Dinar
  "image_prompt":   an image-generation prompt that would render this product in the
                    style of Grand Theft Auto cover art: bold saturated colours, heavy
                    black outlines, cel-shaded comic realism, dramatic lighting,
                    isolated product on a plain background

Product name: {name}
"""

BACKGROUND_REMOVAL_PROMPT = (
    "Remove the background from this product photo completely. Return the product "
    "isolated on a fully transparent background as a PNG with an alpha channel. "
    "Keep the product itself unchanged and uncropped. No backdrop, no shadow, no "
    "surface, no added text."
)


def _client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS))


def _failed(db: Session, admin: User, name: str, message: str) -> AIProductDraft:
    draft = AIProductDraft(
        admin_id=admin.id, requested_name=name, status=AIRequestStatus.FAILED, error_message=message[:500]
    )
    AIProductDraftRepository(db).add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def _extract_json(text: str) -> dict | None:
    """Tolerant JSON extraction.

    The research call cannot use response_schema, because structured output
    and the google_search tool can't be requested together — so the model
    replies with JSON in prose, and may still wrap it in a code fence despite
    being asked not to.
    """
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        braces = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = braces.group(0) if braces else None
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _research(name: str) -> tuple[dict | None, str | None]:
    """Grounded web lookup. Returns (data, error_message)."""
    client = _client()
    last_error = "AI research failed"
    for model in TEXT_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=RESEARCH_PROMPT.format(name=name),
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
            )
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        data = _extract_json(response.text or "")
        if data is None:
            last_error = "The AI did not return usable product details."
            continue
        return data, None
    return None, last_error


def _to_transparent_png(source_png: bytes) -> tuple[bytes, bool, str | None]:
    """Asks an image model to strip the background.

    `source_png` must already be PNG — callers normalize first, so the
    mime_type sent here is always truthful regardless of what format the
    remote site actually served.

    Returns (png_bytes, has_real_transparency, error). Falls back to the
    unmodified source when no model can be reached, so the admin still gets
    something to look at and `has_transparency` tells them honestly that the
    cut-out did not happen.
    """
    client = _client()
    last_error = None
    for model in IMAGE_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=source_png, mime_type="image/png"),
                    types.Part.from_text(text=BACKGROUND_REMOVAL_PROMPT),
                ],
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        for part in _image_parts(response):
            png, has_alpha = _normalize_png(part)
            return png, has_alpha, None
        last_error = "The image model returned no image."

    png, has_alpha = _normalize_png(source_png)
    return png, has_alpha, last_error or "Background removal was unavailable."


def _image_parts(response: object) -> list[bytes]:
    """Every inline image in a response, defensively — a blocked or empty
    candidate must degrade to 'no image', not raise."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    images = []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            images.append(inline.data)
    return images


def _normalize_png(data: bytes) -> tuple[bytes, bool]:
    """Re-encodes to RGBA PNG and reports whether any pixel is actually
    transparent — an alpha channel that is fully opaque is not a cut-out."""
    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGBA")
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        min_alpha = image.getchannel("A").getextrema()[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return buffer.getvalue(), min_alpha < 255


def create_draft(db: Session, admin: User, name: str) -> AIProductDraft:
    name = name.strip()
    if not settings.gemini_api_key:
        return _failed(db, admin, name, "AI assistant is not configured (missing GEMINI_API_KEY).")

    data, error = _research(name)
    if data is None:
        return _failed(db, admin, name, error or "AI research failed.")

    image_url = str(data.get("image_url") or "").strip()
    if not image_url:
        return _failed(db, admin, name, "The AI did not find a product image.")

    try:
        source_bytes, _ = fetch_image(image_url)
    except HTTPException as exc:
        return _failed(db, admin, name, f"Could not use the found image: {exc.detail}")

    try:
        # Normalize to PNG before handing it to the image model, so what we
        # claim as image/png always is one whatever the site served.
        canonical_png, _ = _normalize_png(source_bytes)
        png_bytes, has_transparency, _ = _to_transparent_png(canonical_png)
    except Exception as exc:  # noqa: BLE001
        return _failed(db, admin, name, f"Image processing failed: {exc}")

    draft_id = uuid.uuid4()
    # Staged under the draft's own id: the file is written before any Product
    # exists, and on confirm this exact path becomes the product's image_url
    # rather than being copied again.
    staged_url = save_image(draft_id, png_bytes, ".png")

    price = data.get("suggested_price_iqd")
    draft = AIProductDraft(
        id=draft_id,
        admin_id=admin.id,
        requested_name=name,
        source_url=image_url[:1000],
        source_title=str(data.get("source_title") or "")[:500] or None,
        extracted_name=str(data.get("product_name") or name)[:200],
        extracted_description=str(data.get("description") or ""),
        suggested_price=float(price) if isinstance(price, (int, float)) else None,
        image_prompt=str(data.get("image_prompt") or ""),
        staged_image_url=staged_url,
        has_transparency=has_transparency,
        status=AIRequestStatus.PENDING,
    )
    AIProductDraftRepository(db).add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def confirm_draft(
    db: Session, admin: User, draft_id: uuid.UUID, payload: AIProductDraftConfirm, region: Region
) -> AIProductDraft:
    draft = AIProductDraftRepository(db).get_by_id(draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product draft not found")
    if draft.status != AIRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draft is not pending")

    name = (payload.name or draft.extracted_name or draft.requested_name).strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product name is required")

    price = payload.price if payload.price is not None else (float(draft.suggested_price or 0))
    description = payload.description if payload.description is not None else (draft.extracted_description or "")

    # The ordinary creation path, unchanged: same validation, same region
    # confinement, same repository write as the manual admin form.
    product = product_service.create_product(
        db,
        ProductCreate(
            name=name,
            description=description,
            price=price,
            stock_quantity=payload.stock_quantity,
            image_url=draft.staged_image_url,
        ),
        admin,
        region,
    )

    draft.status = AIRequestStatus.CONFIRMED
    draft.created_product_id = product.id
    draft.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return draft


def reject_draft(db: Session, draft_id: uuid.UUID) -> AIProductDraft:
    draft = AIProductDraftRepository(db).get_by_id(draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product draft not found")
    if draft.status != AIRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draft is not pending")

    draft.status = AIRequestStatus.REJECTED
    db.commit()
    db.refresh(draft)
    return draft


def list_recent(db: Session, limit: int = 20) -> list[AIProductDraft]:
    return AIProductDraftRepository(db).list_recent(limit)
