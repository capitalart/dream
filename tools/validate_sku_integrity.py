#!/usr/bin/env python3
"""Validate SKU-based file integrity for DreamArtMachine.

Scans the unanalysed and processed artwork directories to ensure that
all required assets exist for each SKU. Missing components are logged
and returned as errors.
"""

import json
import logging
import re
import shutil
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SKU_PATTERN = re.compile(r"[A-Z]+-\d+")


def _extract_sku(name: str) -> str | None:
    match = SKU_PATTERN.search(name)
    return match.group(0) if match else None


def check_unanalysed(base: Path) -> list[str]:
    """Validate files in the unanalysed-artwork directory."""
    errors: list[str] = []
    if not base.exists():
        logging.debug("Unanalysed directory %s does not exist", base)
        return errors

    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        qc = next(folder.glob("*-QC.json"), None)
        if not qc:
            errors.append(f"Missing QC JSON in {folder.name}")
            continue
        sku = _extract_sku(qc.name) or folder.name
        stem = qc.stem.replace("-QC", "")
        thumb = folder / f"{stem}-THUMB.jpg"
        analyse = folder / f"{stem}-ANALYSE.jpg"
        original = next(
            (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"} and sku not in p.name),
            None,
        )
        if not original:
            errors.append(f"Missing original for {sku}")
        if not thumb.exists():
            errors.append(f"Missing THUMB for {sku}")
        if not analyse.exists():
            errors.append(f"Missing ANALYSE for {sku}")
    return errors


def check_processed(base: Path) -> list[str]:
    """Validate files in the processed-artwork directory."""
    errors: list[str] = []
    if not base.exists():
        logging.debug("Processed directory %s does not exist", base)
        return errors

    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        sku = None
        for item in folder.iterdir():
            sku = _extract_sku(item.name)
            if sku:
                break
        if not sku:
            errors.append(f"No SKU found in folder {folder.name}")
            continue

        slug = folder.name
        main = folder / f"{slug}-{sku}.jpg"
        thumb = folder / f"{slug}-{sku}-THUMB.jpg"
        analyse = folder / f"{slug}-{sku}-ANALYSE.jpg"
        qc = folder / f"{sku}-QC.json"
        final_json = folder / f"{sku}-FINAL.json"
        thumb_dir = folder / "THUMBS"
        required = [
            (main, "Main"),
            (thumb, "THUMB"),
            (analyse, "ANALYSE"),
            (qc, "QC JSON"),
            (final_json, "Final JSON"),
        ]
        if not thumb_dir.exists():
            errors.append(f"Missing THUMBS folder for {sku} in {slug}")
        for path, desc in required:
            if not path.exists():
                errors.append(f"Missing {desc} for {sku} in {slug}")

        mocks = list(folder.glob(f"{slug}-{sku}-MU-*.jpg"))
        if len(mocks) != 9:
            errors.append(f"Expected 9 mockups for {sku} in {slug}")
        for i in range(1, 10):
            mock = folder / f"{slug}-{sku}-MU-{i:02}.jpg"
            if not mock.exists():
                errors.append(f"Missing mockup MU-{i:02} for {sku} in {slug}")
            mu_thumb = thumb_dir / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg"
            if not mu_thumb.exists():
                errors.append(f"Missing mockup thumb MU-{i:02} for {sku} in {slug}")
        thumbs = list(thumb_dir.glob(f"{slug}-{sku}-MU-*-THUMB.jpg")) if thumb_dir.exists() else []
        if len(thumbs) != 9:
            errors.append(f"Expected 9 mockup thumbs for {sku} in {slug}")
    return errors


def validate(root: Path) -> list[str]:
    """Run SKU integrity validation for both artwork directories."""
    logging.info("Using Python interpreter at: %s", shutil.which("python") or "unknown")
    root = root.resolve()
    load_dotenv(dotenv_path=root / ".env", override=False)
    unanalysed = root / "art-processing" / "unanalysed-artwork"
    processed = root / "art-processing" / "processed-artwork"
    errors = []
    if not (root / ".env").exists():
        errors.append("Missing .env file")
    errors += check_unanalysed(unanalysed) + check_processed(processed)
    if errors:
        for err in errors:
            logging.error(err)
    else:
        logging.info("All SKU assets validated")
    return errors


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    errors = validate(base)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
