"""Where product images live on disk, in one place.

Both the admin's manual upload (routers/products.py) and the AI product
creation flow (services/ai_product_service.py) write through here, so the
storage layout, the size cap and the accepted formats cannot drift apart
between the two paths.
"""

import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "products"
ALLOWED_CONTENT_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
PUBLIC_URL_PREFIX = "/uploads/products"


def save_image(product_id: uuid.UUID, contents: bytes, extension: str) -> str:
    """Writes the bytes under a server-generated name and returns the public
    URL to store on Product.image_url.

    The filename never contains anything the client supplied — only the
    product id, random hex, and an extension the caller took from
    ALLOWED_CONTENT_TYPES — so an uploaded name can't traverse directories
    or land as an executable extension.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{product_id}-{uuid.uuid4().hex[:8]}{extension}"
    (UPLOAD_DIR / filename).write_bytes(contents)
    return f"{PUBLIC_URL_PREFIX}/{filename}"
