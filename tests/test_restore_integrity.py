from pathlib import Path
import sys

# Add project root to import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import validate

def test_full_integrity_passes(tmp_path):
    """
    Simulates a complete and valid project structure and asserts no errors are found.
    """
    # --- Setup a valid structure ---
    root = tmp_path
    (root / ".env").write_text("TEST=1")

    # Unanalysed section
    unanalysed = root / "art-processing" / "unanalysed-artwork" / "img"
    unanalysed.mkdir(parents=True)
    sku1 = "RJC-00001"
    (unanalysed / "img.jpg").write_text("x")
    (unanalysed / f"{sku1}-THUMB.jpg").write_text("x")
    (unanalysed / f"{sku1}-ANALYSE.jpg").write_text("x")
    (unanalysed / f"{sku1}-QC.json").write_text("{}")

    # Processed section
    processed = root / "art-processing" / "processed-artwork" / "slug"
    thumbs = processed / "THUMBS"
    thumbs.mkdir(parents=True)
    sku2 = "RJC-12345"
    slug = processed.name
    (processed / f"{slug}-{sku2}.jpg").write_text("x")
    (processed / f"{slug}-{sku2}-THUMB.jpg").write_text("x")
    (processed / f"{slug}-{sku2}-ANALYSE.jpg").write_text("x")
    (processed / f"{sku2}-QC.json").write_text("{}")
    (processed / f"{sku2}-FINAL.json").write_text("{}")
    for i in range(1, 10):
        (processed / f"{slug}-{sku2}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku2}-MU-{i:02}-THUMB.jpg").write_text("mu")

    # --- Run Validation ---
    errors = validate(root)

    # --- Assert ---
    assert not errors, f"Validation failed with errors: {errors}"