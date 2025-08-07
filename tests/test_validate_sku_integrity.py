from pathlib import Path
import sys
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed, check_processed


def test_missing_thumb(tmp_path):
    root = tmp_path / "unanalysed-artwork" / "image"
    root.mkdir(parents=True)
    sku = "ARTNARRATOR-00001"
    (root / "image.jpg").write_text("data")
    (root / f"{sku}-ANALYSE.jpg").write_text("data")
    (root / f"{sku}-QC.json").write_text("{}")
    errors = check_unanalysed(tmp_path / "unanalysed-artwork")
    assert any("THUMB" in e for e in errors)


def test_all_files_present(tmp_path):
    root = tmp_path / "unanalysed-artwork" / "image"
    root.mkdir(parents=True)
    sku = "ARTNARRATOR-00002"
    (root / "image.jpg").write_text("data")
    (root / f"{sku}-ANALYSE.jpg").write_text("data")
    (root / f"{sku}-THUMB.jpg").write_text("data")
    (root / f"{sku}-QC.json").write_text("{}")
    errors = check_unanalysed(tmp_path / "unanalysed-artwork")
    assert errors == []


def test_processed_missing_final_json(tmp_path):
    base = tmp_path / "processed-artwork" / "slug"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "ARTNARRATOR-12345"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{sku}-QC.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert any("Final JSON" in e for e in errors)


def test_processed_complete(tmp_path):
    base = tmp_path / "processed-artwork" / "slug2"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "ARTNARRATOR-56789"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{sku}-QC.json").write_text("{}")
    (base / f"{sku}-FINAL.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert errors == []
