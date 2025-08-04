import os
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_get_feature_vector(monkeypatch):
    def fake_get_feature_vector(_):
        return [0.1] * 768

    monkeypatch.setattr("retriever.main.get_feature_vector", fake_get_feature_vector)


from retriever.main import app

client = TestClient(app)


@pytest.fixture(scope="session")
def test_image_bytes():
    with open(Path("tests/test_image.jpeg"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def corrupted_image_bytes():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x03"


@pytest.fixture(scope="session")
def invalid_image_bytes():
    return b"This is not a real image."


def test_retriever_health():
    response = client.get(f"/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "OK!"


def test_search_image(test_image_bytes):
    files = {"file": ("test_image.jpeg", test_image_bytes, "image/jpeg")}
    response = client.post(f"/search_image", files=files)
    assert response.status_code == 200

    result = response.json()
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(url.startswith("https://") for url in result)


def test_search_no_file():
    response = client.post(f"/search_image")
    assert response.status_code == 422
