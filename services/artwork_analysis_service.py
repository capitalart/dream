"""Artwork analysis service for DreamArtMachine."""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

try:  # Optional dependency
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None

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

    source = (UNANALYSED_ARTWORK_DIR / filename).resolve()
    if not source.exists():
        logger.error("Analysis failed for %s", filename)
        raise FileNotFoundError(filename)

    stem = Path(filename).stem
    stem = stem.replace("-ANALYSE", "").replace("-analyse", "")
    slug = sanitize_slug(stem)
    slug_dir = (PROCESSED_ARTWORK_DIR / slug).resolve()
    slug_dir.mkdir(parents=True, exist_ok=True)

    processed_image = processed_artwork_path(slug).resolve()
    # Move the original file into the processed artwork directory
    # instead of copying to ensure there is only a single source of
    # truth for the artwork file.
    shutil.move(str(source), str(processed_image))
    logger.info("Moved artwork to %s", processed_image)

    analysis, oa_bytes = _perform_analysis(slug, processed_image)
    analysis_path = processed_analysis_path(slug).resolve()
    _safe_write_json(analysis_path, analysis)
    logger.info("Wrote analysis to %s", analysis_path)

    openai_img = processed_openai_path(slug).resolve()
    with openai_img.open("wb") as fh:
        fh.write(oa_bytes)
    logger.info("Wrote OpenAI image %s", openai_img)

    _update_master_paths(slug, processed_image, analysis_path, openai_img)

    logger.info("Analysis complete for %s", filename)
    return slug


def _perform_analysis(slug: str, image: Path) -> Tuple[Dict[str, Any], bytes]:
    """Run AI analysis for ``image``.

    Returns analysis data and image bytes. Falls back to a mock response
    when OpenAI is unavailable or errors.
    """

    img_path = image.resolve()
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI and api_key:
        try:  # pragma: no cover - network dependent
            client = OpenAI()
            with img_path.open("rb") as fh:
                resp = client.images.generate_variation(
                    model="gpt-image-1", image=fh, timeout=30
                )
            b64_img = resp.data[0].b64_json
            img_bytes = base64.b64decode(b64_img)
            logger.info("OpenAI Vision success for %s", slug)
            return {"provider": "openai", "data": resp.model_dump()}, img_bytes
        except Exception as exc:  # pragma: no cover
            logger.exception("OpenAI analysis failed: %s", exc)
            logger.warning("OpenAI fallback used for %s", slug)
    else:
        logger.warning("OpenAI fallback used for %s", slug)

    with img_path.open("rb") as fh:
        img_bytes = fh.read()
    return {"provider": "mock", "notes": "OpenAI unavailable or errored"}, img_bytes


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
            # Store absolute paths so downstream consumers have the
            # correct locations regardless of the current working
            # directory.
            "image": str(image.resolve()),
            "analysis": str(analysis.resolve()),
            "openai": str(openai_img.resolve()),
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
