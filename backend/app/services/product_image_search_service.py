"""Finding a real product photo to style.

Gemini's own google_search grounding is not available on the free tier — it
returns 429 on the first call of the day, on every model, while plain
generation on the same model succeeds. So image discovery runs through Google's
Programmable Search (Custom Search JSON API) instead, whose free allowance is
100 queries/day.

This module only ever returns candidate URLs. It never fabricates one: with no
credentials, or no results, callers get an empty list and the product draft is
recorded as having no image rather than pointing at a guess.
"""

import httpx

from app.core.config import settings

ENDPOINT = "https://www.googleapis.com/customsearch/v1"
TIMEOUT_SECONDS = 15.0
# More than one candidate so a URL that fails the SSRF/format checks in
# image_fetch_service doesn't end the attempt.
CANDIDATES = 5


class ImageSearchUnavailable(Exception):
    """Search could not run at all (not configured, or the API refused)."""


def build_query(name: str, description: str = "") -> str:
    """Biases the query toward an isolated pack shot rather than a lifestyle
    photo, which is what styles and cuts out cleanly."""
    base = name.strip()
    if description.strip():
        base = f"{base} {description.strip()}"
    return f"{base} product packaging official"


def search_product_images(name: str, description: str = "") -> list[str]:
    """Candidate image URLs, best match first. Empty list means nothing
    usable was found — never a placeholder."""
    if not settings.image_search_configured:
        raise ImageSearchUnavailable(
            "Image search is not configured (missing GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID)."
        )

    params = {
        "key": settings.google_cse_api_key,
        "cx": settings.google_cse_id,
        "q": build_query(name, description),
        "searchType": "image",
        "num": CANDIDATES,
        "safe": "active",
        # Photographs of products, not clip art or line drawings.
        "imgType": "photo",
    }

    try:
        response = httpx.get(ENDPOINT, params=params, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise ImageSearchUnavailable(f"Image search request failed: {type(exc).__name__}")

    if response.status_code == 429:
        raise ImageSearchUnavailable(
            "Google Custom Search free quota is exhausted for today (100 queries/day). "
            "It resets every 24 hours. No paid search was used."
        )
    if response.status_code != 200:
        raise ImageSearchUnavailable(f"Image search returned HTTP {response.status_code}")

    payload = response.json()
    return [item["link"] for item in payload.get("items", []) if item.get("link")]
