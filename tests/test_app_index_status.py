import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

from app.main import app


client = TestClient(app)


def test_index_status() -> None:
    response = client.get("/index/status")

    assert response.status_code == 200

    body = response.json()

    assert body["collection"] == "homelab_bootstrap"
    assert body["incremental_updates"] is True
    assert body["stale_chunk_cleanup"] is True
