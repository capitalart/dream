from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed


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
