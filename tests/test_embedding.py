import os
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient

from embedding.main import app

client = TestClient(app)


@pytest.fixture(scope="session")
def test_image_bytes():
    with open(Path("tests/data/test_image.jpeg"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def invalid_bytes():
    return b"This is not an image at all."


def test_embedding_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_embed_valid_image(test_image_bytes):
    files = {"file": ("test_image.jpeg", test_image_bytes, "image/jpeg")}
    response = client.post("/embed", files=files)
    assert response.status_code == 200
    vector = response.json()
    assert isinstance(vector, list)
    assert len(vector) > 0


def test_embed_invalid_image_type(invalid_bytes):
    files = {"file": ("fake.txt", invalid_bytes, "text/plain")}
    response = client.post("/embed", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image."


def test_embed_no_file():
    response = client.post("/embed")
    assert response.status_code == 422
