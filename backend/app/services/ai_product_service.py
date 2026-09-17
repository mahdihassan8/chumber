"""AI-assisted product creation: research -> image -> admin review -> create.

Gemini is the only provider, and only its free tier is used. Mirrors the
restock assistant's contract deliberately (services/ai_service.py): the AI only
ever *proposes*. A draft row is written, the admin sees exactly what was found,
and nothing becomes a Product until confirm_draft runs the ordinary
product_service.create_product path.

Model selection is kept local to this module rather than imported from
ai_service, because that module's model list differs between the main branch
and the production hardening branch; duplicating three strings is cheaper than
a service that only imports cleanly on one of them.
"""

import io
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
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
from app.services.product_image_search_service import ImageSearchUnavailable, search_product_images
from app.services.product_image_service import save_image
from app.services.product_image_style_service import apply_gta_style

# Free-tier text models only. Each carries its own free daily budget, so one
# being exhausted does not mean the key is — falling through to a sibling is
# still entirely within the free tier. Nothing here is a paid model, and there
# is deliberately no paid fallback: when every one of these is exhausted the
# draft fails with a clear message instead.
#
# Two Gemini features this feature used to rely on are NOT available on the
# free tier — both return 429 on every call regardless of model:
#   * google_search grounding (live web search)
#   * the image generation/editing models (nano-banana family)
# So research runs on plain generation with structured output, and background
# removal runs locally through rembg rather than an image model.
TEXT_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest")
TIMEOUT_MS = 90_000
MAX_IMAGE_DIMENSION = 1024

RESEARCH_PROMPT = """You are helping an admin add a product to a small private marketplace.

Describe the product named below from your own knowledge.

For image_url, give a direct link to a product photo only if you are confident the
URL is real and still reachable; otherwise leave it as an empty string. Never invent
a plausible-looking URL.

For image_prompt, write an image-generation prompt that would render this product in
the style of Grand Theft Auto cover art: bold saturated colours, heavy black
outlines, cel-shaded comic realism, dramatic lighting, isolated product on a plain
background.

suggested_price_iqd is the approximate retail price in Iraqi Dinar, as a number.

Product name: {name}
"""


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


class _ProductResearch(BaseModel):
    """Structured output schema.

    Usable now only because the google_search tool is gone — Gemini rejects a
    response_schema and a tool in the same request, which is why this used to
    be parsed leniently out of prose.
    """

    product_name: str
    description: str
    image_url: str = ""
    source_title: str = ""
    suggested_price_iqd: float = 0
    image_prompt: str = ""


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _research(name: str) -> tuple[_ProductResearch | None, str | None]:
    """Product lookup from the model's own knowledge. Returns (data, error).

    No web search: grounding is a billed feature, and this must stay inside
    the free tier.
    """
    client = _client()
    last_error = "AI research failed."
    all_quota_exhausted = True

    for model in TEXT_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=RESEARCH_PROMPT.format(name=name),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=_ProductResearch
                ),
            )
        except Exception as exc:  # noqa: BLE001
            if not _is_quota_error(exc):
                all_quota_exhausted = False
                last_error = f"{type(exc).__name__}: {exc}"
            continue

        parsed = response.parsed
        if parsed is None:
            all_quota_exhausted = False
            last_error = "The AI did not return usable product details."
            continue
        return parsed, None

    if all_quota_exhausted:
        # Deliberately a dead end: the free tier is the only tier this feature
        # uses, so there is nothing to fall back to and nothing is retried
        # against a paid model.
        return None, (
            "Gemini free-tier quota is exhausted for today. The daily limit is per model and resets "
            "every 24 hours — try again tomorrow. No paid model was used."
        )
    return None, last_error


# u2net is pinned deliberately rather than taking rembg's default.
#
# The current default is BRIA RMBG 2.0: a 1.02 GB model whose inference was
# OOM-killed (exit 137) with 3.8 GB free, and which is licensed for
# non-commercial use only — both disqualifying for a 4 GB box running a
# marketplace. u2net is ~176 MB, permissively licensed, and verified to cut
# out cleanly here.
REMBG_MODEL = "u2net"
_rembg_session = None

# Measured on this codebase: loading u2net and running one 800x800 inference
# peaks around 916 MB RSS. Two at once would be ~1.8 GB on a 4 GB host that is
# also running Postgres, so inference is serialised. FastAPI runs sync
# endpoints in a threadpool, which means without this guard two admins clicking
# at once really could overlap.
_rembg_lock = threading.Semaphore(1)
REMBG_WAIT_SECONDS = 60


def _get_rembg_session():  # noqa: ANN202
    """Loads the model once per process. Building a session per call would
    re-read the whole model off disk every time."""
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session

        _rembg_session = new_session(REMBG_MODEL)
    return _rembg_session


def _to_transparent_png(source_png: bytes) -> tuple[bytes, bool, str | None]:
    """Strips the background locally with rembg.

    Local and free on purpose: the Gemini image models that could do this are
    not available on the free tier, and this runs offline with no quota and no
    per-call cost.

    Returns (png_bytes, has_real_transparency, error). If rembg is unavailable
    or fails — including being OOM-killed on a small host — the original image
    is kept and has_transparency reports False rather than a cut-out being
    faked: the admin sees the truth on the review screen and can still create
    the product.
    """
    if not _rembg_lock.acquire(timeout=REMBG_WAIT_SECONDS):
        png, has_alpha = _normalize_png(source_png)
        return png, has_alpha, "Background removal is busy; the image was kept with its background."

    try:
        from rembg import remove  # imported lazily: heavy, and only this path needs it

        cut_out = remove(source_png, session=_get_rembg_session())
    except Exception as exc:  # noqa: BLE001
        png, has_alpha = _normalize_png(source_png)
        return png, has_alpha, f"Background removal unavailable ({type(exc).__name__})."
    finally:
        _rembg_lock.release()

    png, has_alpha = _normalize_png(cut_out)
    return png, has_alpha, None


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


class ImageStatus:
    """Reporting states for the image pipeline. `OK` is the only one that means
    a usable image was stored; every other value leaves staged_image_url None
    so nothing can mistake a failure for a finished image."""

    OK = "ok"
    NOT_CONFIGURED = "not_configured"
    SEARCH_FAILED = "search_failed"
    NO_RESULTS = "no_results"
    FETCH_FAILED = "fetch_failed"
    PROCESSING_FAILED = "processing_failed"


@dataclass
class ImageOutcome:
    status: str
    staged_image_url: str | None = None
    source_url: str | None = None
    has_transparency: bool = False
    error: str | None = None


def build_product_image(draft_id: uuid.UUID, name: str, description: str) -> ImageOutcome:
    """Find a real product photo, style it, cut it out, store it.

    Deliberately never generates a picture from text: the brief requires the
    *actual* product's packaging, and a generated stand-in would be a different
    product wearing the right name. If no real photo can be found, this reports
    that plainly and stores nothing.

    Never raises — the caller must still get a reviewable draft.
    """
    try:
        candidates = search_product_images(name, description)
    except ImageSearchUnavailable as exc:
        status = ImageStatus.NOT_CONFIGURED if not settings.image_search_configured else ImageStatus.SEARCH_FAILED
        return ImageOutcome(status=status, error=str(exc)[:500])

    if not candidates:
        return ImageOutcome(status=ImageStatus.NO_RESULTS, error="No product image was found for this name.")

    # Walk the candidates: the top hit is often a hotlink-protected CDN or an
    # HTML page wearing an image extension, and the SSRF/format checks in
    # fetch_image reject those. Trying the next one costs nothing.
    last_error = None
    for url in candidates:
        try:
            source_bytes, _ = fetch_image(url)
        except HTTPException as exc:
            last_error = str(exc.detail)
            continue

        try:
            canonical_png, _ = _normalize_png(source_bytes)
            styled = apply_gta_style(canonical_png)
            final_png, has_transparency, removal_error = _to_transparent_png(styled)
            # Staged under the draft's own id: written before any Product
            # exists, and on confirm this exact path becomes the product's
            # image_url rather than being copied again.
            staged_url = save_image(draft_id, final_png, ".png")
        except Exception as exc:  # noqa: BLE001
            return ImageOutcome(
                status=ImageStatus.PROCESSING_FAILED,
                source_url=url[:1000],
                error=f"Image processing failed: {type(exc).__name__}"[:500],
            )

        return ImageOutcome(
            status=ImageStatus.OK,
            staged_image_url=staged_url,
            source_url=url[:1000],
            has_transparency=has_transparency,
            # A cut-out that silently didn't happen is still worth surfacing.
            error=removal_error[:500] if removal_error else None,
        )

    return ImageOutcome(
        status=ImageStatus.FETCH_FAILED,
        error=f"No candidate image could be downloaded. Last reason: {last_error}"[:500],
    )


def retry_image(db: Session, draft_id: uuid.UUID) -> AIProductDraft:
    """Re-runs only the image pipeline for a pending draft, leaving the
    already-reviewed product details alone."""
    draft = AIProductDraftRepository(db).get_by_id(draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product draft not found")
    if draft.status != AIRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Draft is not pending")

    outcome = build_product_image(draft.id, draft.extracted_name or draft.requested_name, draft.extracted_description or "")
    draft.staged_image_url = outcome.staged_image_url
    draft.source_url = outcome.source_url
    draft.has_transparency = outcome.has_transparency
    draft.image_status = outcome.status
    draft.image_error = outcome.error
    db.commit()
    db.refresh(draft)
    return draft


def create_draft(db: Session, admin: User, name: str) -> AIProductDraft:
    name = name.strip()
    if not settings.gemini_api_key:
        return _failed(db, admin, name, "AI assistant is not configured (missing GEMINI_API_KEY).")

    data, error = _research(name)
    if data is None:
        return _failed(db, admin, name, error or "AI research failed.")

    draft_id = uuid.uuid4()
    outcome = build_product_image(draft_id, data.product_name or name, data.description)

    draft = AIProductDraft(
        id=draft_id,
        admin_id=admin.id,
        requested_name=name,
        source_url=outcome.source_url,
        source_title=data.source_title[:500] or None,
        extracted_name=(data.product_name or name)[:200],
        extracted_description=data.description,
        suggested_price=data.suggested_price_iqd or None,
        image_prompt=data.image_prompt,
        staged_image_url=outcome.staged_image_url,
        has_transparency=outcome.has_transparency,
        image_status=outcome.status,
        image_error=outcome.error,
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
