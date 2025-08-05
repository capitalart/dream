"""Generate mockup composites for an artwork slug."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import (
    MOCKUPS_DIR,
    FINALISED_ARTWORK_DIR,
    configure_logging,
    mockup_path,
    sanitize_slug,
    processed_artwork_path,
)

logger = logging.getLogger(__name__)


def generate(slug: str) -> None:
    slug = sanitize_slug(slug)
    source = processed_artwork_path(slug)
    if not source.exists():
        logger.error("Processed image missing: %s", source)
        return

    dest_dir = FINALISED_ARTWORK_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as art:
        templates = sorted(MOCKUPS_DIR.glob("*.jpg"))[:9]
        for idx, tmpl in enumerate(templates, 1):
            out_path = mockup_path(slug, idx)
            if out_path.exists():
                logger.info("Mockup already exists: %s", out_path)
                continue
            with Image.open(tmpl) as background:
                if background.size != art.size:
                    logger.warning(
                        "Size mismatch %s vs %s, skipping %s",
                        background.size,
                        art.size,
                        tmpl,
                    )
                    continue
                composite = background.copy()
                composite.paste(art, (0, 0))
                composite.save(out_path)
                logger.info("Saved %s", out_path)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Generate mockup composites")
    parser.add_argument("slug", help="Artwork slug")
    args = parser.parse_args()
    generate(args.slug)


if __name__ == "__main__":
    main()

