# services/artwork_analysis_service.py
# ======================================================================
# Artwork analysis service for DreamArtMachine
# ----------------------------------------------------------------------
# This version accepts a RELATIVE path and a resolved absolute src_path
# (pointing to the ANALYSE image inside UNANALYSED/<slug>/). It moves
# that file into the processed area, runs analysis (with robust fallback),
# writes outputs, updates the master registry atomically, and returns slug.
# ======================================================================

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from flask import current_app

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

# Optional OpenAI dependency
try:  # pragma: no cover (networked SDK)
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None


def analyze_artwork(
    rel_path: str,
    src_path: Path,
    aspect: str,
    provider: str = "openai",
    slug_hint: Optional[str] = None,
    filename_hint: Optional[str] = None,
) -> str:
    """
    Run artwork analysis for an ANALYSE image located at UNANALYSED/<slug>/<file>.

    Args:
        rel_path: Path relative to UNANALYSED root, e.g. "slug/slug-ANALYSE.jpg".
        src_path: Resolved absolute path to the ANALYSE image (must exist).
        aspect:   Aspect label like "square", "4x5", etc. (for logging/flows).
        provider: "openai" (default) or others if supported.
        slug_hint: Optional precomputed slug (first folder name).
        filename_hint: Optional filename (for logging only).

    Returns:
        slug (str): The slug used for downstream pages (e.g., /edit-listing/<slug>).

    Raises:
        FileNotFoundError: If src_path does not exist or is out of scope.
        ValueError: If a slug cannot be derived.
    """
    # --- Validate path scope & existence ---------------------------------
    root_real = UNANALYSED_ARTWORK_DIR.resolve()
    if not src_path.is_absolute():
        src_path = src_path.resolve()

    if not src_path.exists():
        logger.error("Source not found: %s", src_path)
        raise FileNotFoundError(src_path)

    # Prevent escaping outside the UNANALYSED root
    if not str(src_path).startswith(str(root_real)):
        logger.error("Out-of-scope source path: %s", src_path)
        raise FileNotFoundError(src_path)

    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        logger.error("Invalid rel_path: %s", rel_path)
        raise FileNotFoundError(rel_path)

    # --- Derive slug & filename ------------------------------------------
    filename = filename_hint or rel.name
    # Old convention: slug comes from <filename> stem before "-ANALYSE"
    stem = Path(filename).stem
    stem_base = stem.replace("-ANALYSE", "").replace("-analyse", "")
    # Prefer slug from folder; fallback to sanitized stem
    slug = slug_hint or (rel.parts[0] if rel.parts else sanitize_slug(stem_base))
    if not slug:
        raise ValueError(f"Could not determine slug from rel_path: {rel_path}")

    # Final safety: normalize slug
    slug = sanitize_slug(slug)

    current_app.logger.info(
        "Analysis start | slug=%s file=%s aspect=%s provider=%s", slug, filename, aspect, provider
    )

    # Ensure processed folder exists
    (PROCESSED_ARTWORK_DIR / slug).mkdir(parents=True, exist_ok=True)

    # --- Move ANALYSE image into processed area as the main artwork -------
    processed_image = processed_artwork_path(slug).resolve()
    # If a previous processed file exists, remove it to avoid collisions
    try:
        if processed_image.exists():
            processed_image.unlink()
    except Exception:  # pragma: no cover
        logger.exception("Failed to remove existing processed image: %s", processed_image)

    shutil.move(str(src_path), str(processed_image))
    logger.info("Moved artwork to %s", processed_image)

    # --- Perform analysis (with robust fallback) --------------------------
    analysis, oa_bytes = _perform_analysis(slug, processed_image, provider)

    # --- Write analysis JSON ----------------------------------------------
    analysis_path = processed_analysis_path(slug).resolve()
    _safe_write_json(analysis_path, analysis)
    logger.info("Wrote analysis JSON: %s", analysis_path)

    # --- Write OpenAI (or fallback) image ---------------------------------
    openai_img = processed_openai_path(slug).resolve()
    try:
        with openai_img.open("wb") as fh:
            fh.write(oa_bytes)
        logger.info("Wrote OpenAI image: %s", openai_img)
    except Exception:  # pragma: no cover
        logger.exception("Failed writing OpenAI image for %s", slug)

    # --- Update master registry atomically --------------------------------
    _update_master_paths(slug, processed_image, analysis_path, openai_img)

    current_app.logger.info("Analysis complete | slug=%s", slug)
    return slug


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------
def _perform_analysis(slug: str, image: Path, provider: str) -> Tuple[Dict[str, Any], bytes]:
    """
    Run AI analysis for `image` and return (analysis_json, image_bytes).

    - If OpenAI is configured, try to generate a derivative.
    - On any failure (or if not configured), fall back to raw bytes.
    """
    img_path = image.resolve()
    api_key = os.getenv("OPENAI_API_KEY")

    if OpenAI and api_key and provider.lower() == "openai":  # pragma: no cover
        try:
            client = OpenAI()
            # Using "gpt-image-1" with a minimal variation-style call if supported,
            # otherwise fallback gets triggered below.
            with img_path.open("rb") as fh:
                # Prefer generate() where available; some environments used variations.
                # If this raises, we'll fallback gracefully.
                resp = client.images.generate(
                    model="gpt-image-1",
                    prompt="Create a subtle derivative preview of the artwork (for internal analysis).",
                    image=fh,  # some SDKs ignore this param; safe to try
                )
            # Expect base64 output in data[0].b64_json (older SDKs)
            b64_img = getattr(resp.data[0], "b64_json", None)
            if b64_img:
                img_bytes = base64.b64decode(b64_img)
                logger.info("OpenAI image generated for %s", slug)
                # Store the raw model payload minimally to keep file sizes reasonable
                analysis = {"provider": "openai", "model": getattr(resp, "model", "gpt-image-1")}
                return analysis, img_bytes
            logger.warning("OpenAI response missing b64_json; falling back. slug=%s", slug)
        except Exception as exc:
            logger.exception("OpenAI analysis failed for %s: %s", slug, exc)
            logger.warning("OpenAI fallback used for %s", slug)

    # Fallback: no OpenAI or error — return the source bytes so pipelines continue
    with img_path.open("rb") as fh:
        img_bytes = fh.read()
    return {"provider": "mock", "notes": "OpenAI unavailable or error; used source bytes"}, img_bytes


def _safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid partial files."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    tmp.replace(path)


def _update_master_paths(slug: str, image: Path, analysis: Path, openai_img: Path) -> None:
    """
    Update master-artwork-paths.json atomically with absolute paths.

    Structure:
        {
          "<slug>": {
            "image":   "<abs path>",
            "analysis":"<abs path>",
            "openai":  "<abs path>"
          },
          ...
        }
    """
    record = {
        slug: {
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
