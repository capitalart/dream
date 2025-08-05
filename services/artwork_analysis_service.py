"""Artwork analysis service for DreamArtMachine."""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict

try:  # Optional dependencies
    import openai  # type: ignore
except Exception:  # pragma: no cover
    openai = None

from config import (
    MASTER_ARTWORK_PATHS_FILE,
    PROCESSED_ARTWORK_DIR,
    UNANALYSED_ARTWORK_DIR,
    sanitize_slug,
    processed_analysis_path,
    processed_artwork_path,
    processed_openai_path,
)

logger = logging.getLogger(__name__)


def analyze_artwork(filename: str) -> str:
    """Analyse ``filename`` and persist analysis and placeholders.

    Parameters
    ----------
    filename:
        Name of the file located within ``UNANALYSED_ARTWORK_DIR``.

    Returns
    -------
    str
        The slug generated from ``filename``.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    """

    source = UNANALYSED_ARTWORK_DIR / filename
    if not source.exists():
        logger.error("Source file missing: %s", source)
        raise FileNotFoundError(filename)

    slug = sanitize_slug(Path(filename).stem)
    slug_dir = PROCESSED_ARTWORK_DIR / slug
    slug_dir.mkdir(parents=True, exist_ok=True)

    processed_image = processed_artwork_path(slug)
    shutil.copyfile(source, processed_image)
    logger.info("Copied artwork to %s", processed_image)

    analysis = _perform_analysis(processed_image)
    analysis_path = processed_analysis_path(slug)
    _safe_write_json(analysis_path, analysis)
    logger.info("Wrote analysis to %s", analysis_path)

    openai_img = processed_openai_path(slug)
    shutil.copyfile(processed_image, openai_img)
    logger.info("Created placeholder image %s", openai_img)

    _update_master_paths(slug, processed_image, analysis_path, openai_img)

    logger.info("Analysis complete for %s", filename)
    return slug


def _perform_analysis(image: Path) -> Dict[str, Any]:
    """Run AI analysis for ``image``.

    Falls back to a mock response when no provider is available.
    """

    if openai and os.getenv("OPENAI_API_KEY"):
        try:  # pragma: no cover - network dependent
            resp = openai.Image.create_variation(image=open(image, "rb"))
            return {"provider": "openai", "data": resp}
        except Exception as exc:  # pragma: no cover
            logger.exception("OpenAI analysis failed: %s", exc)

    logger.warning("Using mock analysis for %s", image)
    return {"provider": "mock", "notes": "analysis unavailable"}


def _safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(path)


def _update_master_paths(
    slug: str, image: Path, analysis: Path, openai_img: Path
) -> None:
    """Update master-artwork-paths.json atomically."""

    record = {
        slug: {
            "image": str(image),
            "analysis": str(analysis),
            "openai": str(openai_img),
        }
    }

    data: Dict[str, Any] = {}
    if MASTER_ARTWORK_PATHS_FILE.exists():
        try:
            with MASTER_ARTWORK_PATHS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # pragma: no cover
            logger.exception("Failed to read %s", MASTER_ARTWORK_PATHS_FILE)

    data.update(record)

    tmp = MASTER_ARTWORK_PATHS_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(MASTER_ARTWORK_PATHS_FILE)

