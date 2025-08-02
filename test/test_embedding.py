import requests
import pytest
from pathlib import Path

EMBEDDING_URL = "http://localhost:5000"

@pytest.fixture(scope="session")
def test_image_bytes():
    with open(Path("test/test_image.jpeg"), "rb") as f:
        return f.read()

@pytest.fixture(scope="session")
def invalid_bytes():
    return b"This is not an image at all."

def test_embedding_health():
    response = requests.get(f"{EMBEDDING_URL}/health_check")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_embed_valid_image(test_image_bytes):
    files = {"file": ("test_image.jpeg", test_image_bytes, "image/jpeg")}
    response = requests.post(f"{EMBEDDING_URL}/embed", files=files)
    assert response.status_code == 200
    vector = response.json()
    assert isinstance(vector, list)
    assert len(vector) > 0

def test_embed_invalid_image_type(invalid_bytes):
    files = {"file": ("fake.txt", invalid_bytes, "text/plain")}
    response = requests.post(f"{EMBEDDING_URL}/embed", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image."

def test_embed_no_file():
    response = requests.post(f"{EMBEDDING_URL}/embed")
    assert response.status_code == 422  # Unprocessable Entity (validation error)
