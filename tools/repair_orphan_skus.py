#!/usr/bin/env python3
"""Scan artwork folders for images lacking SKUs and optionally repair them."""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Iterable

from PIL import Image

SKU_PATTERN = re.compile(r"RJC-[A-Za-z0-9-]+")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def has_sku(path: Path) -> bool:
    return SKU_PATTERN.search(path.stem) is not None


def generate_derivatives(src: Path, sku: str) -> None:
    """Generate THUMB (2000px) and ANALYSE (3800px) images."""
    img = Image.open(src)
    thumb = src.with_name(f"{src.stem}-THUMB{src.suffix}")
    analyse = src.with_name(f"{src.stem}-ANALYSE{src.suffix}")
    img.resize((2000, 2000)).save(thumb)
    img.resize((3800, 3800)).save(analyse)


def repair_file(path: Path, sku: str, auto: bool) -> None:
    if auto:
        new_name = f"{path.stem}-{sku}{path.suffix}"
        new_path = path.with_name(new_name)
        path.rename(new_path)
        generate_derivatives(new_path, sku)
        logging.info("Repaired orphan %s", new_path.name)
    else:
        logging.warning("Orphan found: %s", path.name)


def scan(directory: Path, sku: str, auto: bool) -> None:
    for file in directory.glob("*.jpg"):
        if not has_sku(file):
            repair_file(file, sku, auto)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repair orphaned SKU images")
    parser.add_argument("directory", nargs="?", default="art-processing/unanalysed-artwork")
    parser.add_argument("--sku", help="SKU to assign to orphan files")
    parser.add_argument("--auto", action="store_true", help="Automatically rename and generate derivatives")
    args = parser.parse_args(argv)

    directory = Path(args.directory)
    if not directory.exists():
        logging.error("Directory not found: %s", directory)
        return 1
    if args.auto and not args.sku:
        logging.error("--auto requires --sku to be specified")
        return 1

    scan(directory, args.sku or "RJC-0000", args.auto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
