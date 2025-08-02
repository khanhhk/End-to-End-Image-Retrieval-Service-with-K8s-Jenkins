import requests
import pytest
from pathlib import Path

RETRIEVER_URL = "http://localhost:5002"

@pytest.fixture(scope="session")
def test_image_bytes():
    with open(Path("test/test_image.jpeg"), "rb") as f:
        return f.read()

@pytest.fixture(scope="session")
def corrupted_image_bytes():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x03"

@pytest.fixture(scope="session")
def invalid_image_bytes():
    return b"This is not a real image."

def test_retriever_health():
    response = requests.get(f"{RETRIEVER_URL}/health_check")
    assert response.status_code == 200
    assert response.json()["status"] == "OK!"

def test_search_image(test_image_bytes):
    files = {"file": ("test_image.jpeg", test_image_bytes, "image/jpeg")}
    response = requests.post(f"{RETRIEVER_URL}/search_image", files=files)
    assert response.status_code == 200

    result = response.json()
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(url.startswith("https://") for url in result)

def test_search_no_file():
    response = requests.post(f"{RETRIEVER_URL}/search_image")
    assert response.status_code == 422
