import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_login_required_on_artworks(client):
    response = client.get("/artworks")
    assert response.status_code in (302, 401)


def test_login_page_accessible(client):
    assert client.get("/login").status_code == 200
