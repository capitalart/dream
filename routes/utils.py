from __future__ import annotations

"""Utility functions for artwork routes."""

# ==========================================================================
# 1. Imports
# ==========================================================================
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from flask import url_for
from PIL import Image

import config

logger = logging.getLogger(__name__)

# Allowed image extensions for artwork files
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}


# ==========================================================================
# 2. Data Structures
# ==========================================================================
@dataclass
class Artwork:
    """Represents a discovered artwork file."""

    filename: str
    slug: str
    path: Path
    aspect: str
    timestamp: float
    status: str = "unanalysed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "slug": self.slug,
            "path": str(self.path),
            "aspect": self.aspect,
            "timestamp": self.timestamp,
            "status": self.status,
        }


# ==========================================================================
# 3. Artwork Discovery & Registry
# ==========================================================================
def _aspect_from_image(path: Path) -> str:
    """Return a simple aspect label for the given image path."""
    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception as exc:  # pragma: no cover - unexpected image errors
        logger.warning("Failed to read image %s: %s", path, exc)
        return "unknown"

    if height == 0:
        return "unknown"

    ratio = width / height
    aspect_map = {
        "square": 1.0,
        "4x5": 0.8,
        "5x4": 1.25,
        "3x4": 0.75,
        "4x3": 1.3333333333,
        "16x9": 16 / 9,
        "9x16": 9 / 16,
    }
    # Choose the aspect with minimal difference
    label = min(aspect_map, key=lambda k: abs(ratio - aspect_map[k]))
    return label


def get_all_unanalysed_artworks() -> List[Dict[str, Any]]:
    """Return metadata for all images awaiting analysis.

    Scans :data:`config.UNANALYSED_ARTWORK_DIR` for image files and returns
    a list of dictionaries containing filename, slug, timestamp, and aspect
    ratio label.
    """
    artworks: List[Artwork] = []
    directory = config.UNANALYSED_ARTWORK_DIR
    if not directory.exists():
        logger.debug("Unanalysed directory missing: %s", directory)
        return []

    for file in sorted(directory.iterdir()):
        if file.suffix.lower() not in _ALLOWED_EXTS or not file.is_file():
            continue
        slug = file.stem
        aspect = _aspect_from_image(file)
        ts = file.stat().st_mtime
        artworks.append(Artwork(file.name, slug, file, aspect, ts))

    return [a.to_dict() for a in artworks]


def register_artwork_in_master(slug: str, path: Path) -> None:
    """Register ``slug`` to ``path`` within master-artwork-paths.json."""
    record = {slug: {"image": str(path.resolve())}}
    master = config.MASTER_ARTWORK_PATHS_FILE
    data: Dict[str, Any] = {}
    if master.exists():
        try:
            data = json.loads(master.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Corrupted master artwork registry: %s", master)
            data = {}
    data.update(record)
    tmp = master.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(master)


# ==========================================================================
# 4. URL Helpers
# ==========================================================================
def get_artwork_image_url(artwork_status: str, filename: str) -> str:
    """Return the correct route URL for an artwork image."""
    status = artwork_status.lower()
    if status == "finalised":
        endpoint = "artwork.finalised_image"
    elif status == "processed":
        endpoint = "artwork.processed_image"
    else:  # default to unanalysed
        endpoint = "artwork.unanalysed_image"
    try:
        return url_for(endpoint, filename=filename)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to build URL for %s: %s", filename, exc)
        return "#"
