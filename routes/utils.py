from __future__ import annotations

"""Utility functions for artwork routes."""

# ==========================================================================
# 1. Imports
# ==========================================================================
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
# 2. Artwork Discovery & Registry
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
    """Return metadata for artworks awaiting analysis.

    The function scans every sub-folder in ``UNANALYSED_ARTWORK_DIR`` and
    collects information about the original upload, generated thumbnail and
    analyse image.  Artworks that already have a matching SKU inside the
    processed folder are skipped.
    """

    directory = config.UNANALYSED_ARTWORK_DIR
    processed_dir = config.PROCESSED_ARTWORK_DIR
    if not directory.exists():
        logger.debug("Unanalysed directory missing: %s", directory)
        return []

    def _find_with_marker(folder: Path, marker: str) -> Path | None:
        """Return the first file in ``folder`` containing ``marker``."""
        for path in folder.glob(f"*{marker}*"):
            if path.suffix.lower() in _ALLOWED_EXTS:
                return path
        return None

    artworks: List[Dict[str, Any]] = []
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir():
            continue
        logger.debug("Scanning %s", folder)

        original = next(
            (
                f
                for f in folder.iterdir()
                if f.is_file()
                and f.suffix.lower() in _ALLOWED_EXTS
                and "-THUMB" not in f.stem
                and "-ANALYSE" not in f.stem
            ),
            None,
        )
        if not original:
            logger.debug("Original missing for %s", folder)
            continue

        thumb = _find_with_marker(folder, "-THUMB")
        if not thumb:
            logger.warning("Missing thumbnail for %s", folder)

        analyse = _find_with_marker(folder, "-ANALYSE")
        if not analyse:
            logger.warning("Missing analyse image for %s", folder)

        sku = thumb.stem.split("-")[0] if thumb else None
        if sku and any(processed_dir.rglob(f"*{sku}*")):
            logger.debug("Skipping already processed artwork %s", sku)
            continue

        aspect = _aspect_from_image(analyse) if analyse else "unknown"
        ts = original.stat().st_mtime
        artworks.append(
            {
                "filename": original.name,
                "slug": folder.name,
                "sku": sku,
                "thumb_path": str(thumb.relative_to(directory)) if thumb else None,
                "analyse": str(analyse.relative_to(directory)) if analyse else None,
                "aspect": aspect,
                "timestamp": ts,
            }
        )
    return artworks


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
