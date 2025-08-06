from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed, check_processed


def test_missing_thumb(tmp_path):
    base = tmp_path / "unanalysed-artwork"
    base.mkdir()
    (base / "image-RJC-0001.jpg").write_text("data")
    (base / "image-RJC-0001-ANALYSE.jpg").write_text("data")
    (base / "image-RJC-0001.json").write_text("{}")
    errors = check_unanalysed(base)
    assert any("THUMB" in e for e in errors)


def test_all_files_present(tmp_path):
    base = tmp_path / "unanalysed-artwork"
    base.mkdir()
    (base / "image-RJC-0002.jpg").write_text("data")
    (base / "image-RJC-0002-ANALYSE.jpg").write_text("data")
    (base / "image-RJC-0002-THUMB.jpg").write_text("data")
    (base / "image-RJC-0002.json").write_text("{}")
    errors = check_unanalysed(base)
    assert errors == []


def test_processed_missing_final_json(tmp_path):
    base = tmp_path / "processed-artwork" / "slug"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-1234"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{slug}-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert any("Final JSON" in e for e in errors)


def test_processed_complete(tmp_path):
    base = tmp_path / "processed-artwork" / "slug2"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-5678"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{slug}-{sku}.json").write_text("{}")
    (base / f"final-{slug}-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert errors == []
