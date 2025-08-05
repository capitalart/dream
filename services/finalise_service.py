"""Finalisation utilities for DreamArtMachine."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Dict

from PIL import Image

from config import (
    FINALISED_ARTWORK_DIR,
    MASTER_ARTWORK_PATHS_FILE,
    mockup_path,
    finalised_artwork_path,
    processed_artwork_path,
    preview_path,
    sanitize_slug,
)

logger = logging.getLogger(__name__)

PREVIEW_WIDTH = 2000
PREVIEW_MAX_BYTES = 600 * 1024


def finalise_artwork(slug: str, metadata: Dict[str, str]) -> None:
    """Finalise ``slug`` artwork using ``metadata``."""
    slug = sanitize_slug(slug)
    source = processed_artwork_path(slug)
    if not source.exists():
        logger.error("Processed image missing: %s", source)
        raise FileNotFoundError(str(source))

    for i in range(1, 10):
        m_path = mockup_path(slug, i)
        if not m_path.exists():
            logger.error("Missing mockup: %s", m_path)
            raise FileNotFoundError(str(m_path))

    dest_dir = FINALISED_ARTWORK_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    final_path = finalised_artwork_path(slug)
    shutil.copyfile(source, final_path)
    logger.info("Copied artwork to %s", final_path)

    preview = preview_path(slug)
    if preview.exists():
        logger.info("Preview already exists: %s", preview)
    else:
        _generate_preview(final_path, preview)
        logger.info("Generated preview %s", preview)

    _update_master_paths(slug, final_path, preview, metadata)
    logger.info("Finalisation complete for %s", slug)


def _generate_preview(source: Path, dest: Path) -> None:
    with Image.open(source) as img:
        width, height = img.size
        if width != PREVIEW_WIDTH:
            ratio = PREVIEW_WIDTH / width
            img = img.resize((PREVIEW_WIDTH, int(height * ratio)), Image.LANCZOS)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        quality = 95
        while True:
            img.save(tmp, format="JPEG", quality=quality, optimize=True)
            if tmp.stat().st_size <= PREVIEW_MAX_BYTES or quality <= 25:
                break
            quality -= 5
        tmp.replace(dest)


def _update_master_paths(
    slug: str, final_path: Path, preview: Path, metadata: Dict[str, str]
) -> None:
    record = {
        slug: {
            "image": str(final_path),
            "preview": str(preview),
            "mockups": [str(mockup_path(slug, i)) for i in range(1, 10)],
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "primary_colour": metadata.get("primary_colour", ""),
            "secondary_colour": metadata.get("secondary_colour", ""),
            "status": "finalised",
        }
    }

    data: Dict[str, object] = {}
    if MASTER_ARTWORK_PATHS_FILE.exists():
        try:
            with MASTER_ARTWORK_PATHS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # pragma: no cover
            logger.exception("Failed reading %s", MASTER_ARTWORK_PATHS_FILE)

    data.update(record)

    tmp = MASTER_ARTWORK_PATHS_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(MASTER_ARTWORK_PATHS_FILE)
