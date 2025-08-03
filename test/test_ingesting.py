import os
import sys
import time
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from ingesting.main import app

client = TestClient(app)


@pytest.fixture(scope="session")
def test_image_bytes():
    with open(Path("test/test_image.jpeg"), "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def corrupted_image_bytes():
    # JPEG header + truncated data
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x03"


@pytest.fixture(scope="session")
def invalid_image_bytes():
    return b"This is not an image."


def test_ingesting_health():
    response = client.get(f"/health_check")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_push_image(test_image_bytes):
    files = {"file": ("test_image.jpeg", test_image_bytes, "image/jpeg")}
    response = client.post(f"/push_image", files=files)
    assert response.status_code == 200

    json_data = response.json()
    assert "file_id" in json_data
    assert "gcs_path" in json_data
    assert "signed_url" in json_data
    time.sleep(2)  # wait Pinecone index


def test_push_no_file():
    response = client.post(f"/push_image")
    assert response.status_code == 422  # validation error (missing file)
