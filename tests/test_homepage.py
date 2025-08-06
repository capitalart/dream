import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "robbie", "password": "Kanga123!"})


def test_home_requires_login(client):
    resp = client.get("/home")
    assert resp.status_code in (302, 401)
    assert "/login" in resp.headers.get("Location", "")


def test_root_redirects_to_home(client):
    login(client)
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/home")


def test_homepage_content(client):
    login(client)
    resp = client.get("/home")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "home-hero" in html
    assert "workflow-row" in html
    assert "site-footer" in html
