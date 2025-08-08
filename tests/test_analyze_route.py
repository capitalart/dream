import importlib.util
import shutil
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
import config

spec = importlib.util.spec_from_file_location("real_app", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
create_app = module.create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "robbie", "password": "Kanga123!"})


def _create_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (10, 10), color="white")
    img.save(path)


def test_analyze_route_smoke(client):
    login(client)
    slug = "test-art"
    filename = f"{slug}-ANALYSE.jpg"
    rel_path = Path(slug) / filename
    _create_image(config.UNANALYSED_ARTWORK_DIR / rel_path)

    resp = client.post(
        f"/analyze/square/{rel_path}",
        data={"provider": "openai"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "redirect_url" in data

    processed_img = config.PROCESSED_ARTWORK_DIR / slug / f"{slug}.jpg"
    assert processed_img.exists()

    shutil.rmtree(config.PROCESSED_ARTWORK_DIR / slug, ignore_errors=True)
    shutil.rmtree(config.UNANALYSED_ARTWORK_DIR / slug, ignore_errors=True)
