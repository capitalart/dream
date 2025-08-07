from __future__ import annotations

import json
import logging
from pathlib import Path

from config import SKU_DIGITS, SKU_PREFIX

logger = logging.getLogger(__name__)


def get_next_sku(tracker: Path) -> str:
    """Return the next sequential SKU and update ``tracker``.

    The tracker JSON stores the last used number. This function is
    intentionally simple and not meant for heavy concurrency.
    """
    tracker.parent.mkdir(parents=True, exist_ok=True)
    last = 0
    if tracker.exists():
        try:
            data = json.loads(tracker.read_text())
            last = int(data.get("last", 0))
        except Exception as exc:  # pragma: no cover - corrupt tracker
            logger.warning("Failed reading SKU tracker %s: %s", tracker, exc)
    next_num = last + 1
    tracker.write_text(json.dumps({"last": next_num}))
    sku = f"{SKU_PREFIX}-{next_num:0{SKU_DIGITS}d}"
    logger.info("Assigned new SKU %s", sku)
    return sku
