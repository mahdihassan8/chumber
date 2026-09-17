"""The GTA-inspired look, applied as a filter rather than a redraw.

This is deliberately *not* a generative model. The brief requires the real
product's brand, logo, typography, packaging, colours, shape and proportions to
survive untouched — and a filter guarantees that by construction: every output
pixel is a function of the corresponding input pixels, so there is no mechanism
by which a logo could be redrawn or a brand invented. A generative editor can
make a prettier poster, but it can also quietly rewrite the text on a can, which
is exactly what the brief forbids.

The look is built from four moves, which together approximate cel-shaded game
cover art:

  1. saturation and contrast lift      -> the punchy, poster-like palette
  2. edge-preserving smoothing         -> flattens photographic noise into areas
  3. posterisation                     -> collapses gradients into flat cel bands
  4. dark edge overlay                 -> the heavy hand-drawn black outline

Runs locally on CPU in well under a second, needs no API, and adds no
dependency: Pillow and numpy are already present.
"""

import io

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

SATURATION = 1.45
CONTRAST = 1.2
# Levels per channel after posterising. Low enough to read as cel bands, high
# enough that packaging artwork stays legible.
POSTERIZE_BITS = 4
SMOOTHING_RADIUS = 2
# Below this edge strength a pixel is not considered an outline. Tuned so
# product silhouettes and lettering outline, but JPEG noise does not.
EDGE_THRESHOLD = 28
OUTLINE_DARKNESS = 0.12


def _outline_mask(grayscale: Image.Image) -> np.ndarray:
    """Edge strength, as a 0..1 array where 1 is 'definitely an outline'."""
    edges = grayscale.filter(ImageFilter.FIND_EDGES)
    edges = edges.filter(ImageFilter.MaxFilter(3))  # thicken to a hand-drawn weight
    data = np.asarray(edges, dtype=np.float32)
    mask = (data - EDGE_THRESHOLD) / max(255 - EDGE_THRESHOLD, 1)
    return np.clip(mask, 0.0, 1.0)


def apply_gta_style(png_bytes: bytes) -> bytes:
    """Styles an RGBA PNG and returns an RGBA PNG.

    Any alpha channel is carried through untouched, so this composes in either
    order with background removal.
    """
    with Image.open(io.BytesIO(png_bytes)) as source:
        image = source.convert("RGBA")
        alpha = image.getchannel("A")
        rgb = image.convert("RGB")

        rgb = ImageEnhance.Color(rgb).enhance(SATURATION)
        rgb = ImageEnhance.Contrast(rgb).enhance(CONTRAST)

        # SMOOTH_MORE then a median pass: flattens photographic texture into
        # paintable areas while keeping boundaries reasonably crisp.
        flattened = rgb.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.MedianFilter(SMOOTHING_RADIUS * 2 + 1))

        # Posterising is what turns smooth shading into discrete cel bands.
        celled = flattened.quantize(colors=2**POSTERIZE_BITS, method=Image.Quantize.MEDIANCUT).convert("RGB")

        mask = _outline_mask(rgb.convert("L"))[:, :, None]
        celled_array = np.asarray(celled, dtype=np.float32)
        # Multiply toward black along edges rather than pasting flat black, so
        # outlines keep some of the underlying colour and read as ink.
        outlined = celled_array * (1.0 - mask * (1.0 - OUTLINE_DARKNESS))

        styled = Image.fromarray(np.clip(outlined, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")
        styled.putalpha(alpha)

        buffer = io.BytesIO()
        styled.save(buffer, format="PNG")
    return buffer.getvalue()
