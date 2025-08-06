from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import validate


def test_restore_integrity(tmp_path):
    root = tmp_path
    (root / ".env").write_text("TEST=1")
    unanalysed = root / "art-processing" / "unanalysed-artwork"
    unanalysed.mkdir(parents=True)
    (unanalysed / "img-RJC-1.jpg").write_text("x")
    (unanalysed / "img-RJC-1-THUMB.jpg").write_text("x")
    (unanalysed / "img-RJC-1-ANALYSE.jpg").write_text("x")
    (unanalysed / "img-RJC-1.json").write_text("{}")

    processed = root / "art-processing" / "processed-artwork" / "slug"
    thumbs = processed / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-1"
    (processed / f"slug-{sku}.jpg").write_text("x")
    (processed / f"slug-{sku}-THUMB.jpg").write_text("x")
    (processed / f"slug-{sku}-ANALYSE.jpg").write_text("x")
    (processed / f"slug-{sku}.json").write_text("{}")
    (processed / f"final-slug-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (processed / f"slug-{sku}-MU-{i:02}.jpg").write_text("x")
        (thumbs / f"slug-{sku}-MU-{i:02}-THUMB.jpg").write_text("x")

    errors = validate(root)
    assert errors == []
