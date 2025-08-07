"""Configure Pillow to handle very large images safely.

This module disables Pillow's decompression bomb protection for the
application while logging any images that cross a safety threshold.  It is
imported once at startup so the configuration is applied globally.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from PIL import Image

# Allow ultra-large artwork. Pillow will no longer raise
# ``DecompressionBombWarning`` based on pixel count.
Image.MAX_IMAGE_PIXELS = None

# Suppress the specific warning but keep other warnings intact.
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

logger = logging.getLogger(__name__)

# Threshold used to flag unusually large images for manual review.
# 100 million pixels roughly corresponds to a 10k x 10k image.
_LARGE_IMAGE_THRESHOLD = 100_000_000

_original_open = Image.open

def _open_with_logging(fp: Any, *args: Any, **kwargs: Any) -> Image.Image:
    """Open an image and log if it is extremely large."""
    image = _original_open(fp, *args, **kwargs)
    try:
        pixels = image.width * image.height
        if pixels > _LARGE_IMAGE_THRESHOLD:
            filename = getattr(image, "filename", getattr(fp, "name", "<unknown>"))
            logger.warning(
                "\U0001F4E6 Large image loaded: %s (%dx%d)",
                filename,
                image.width,
                image.height,
            )
    except Exception:  # pragma: no cover - defensive logging
        pass
    return image

# Monkey-patch Image.open so every usage in the app benefits from logging.
Image.open = _open_with_logging  # type: ignore[assignment]
