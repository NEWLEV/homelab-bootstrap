import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app


client = TestClient(app)


def test_ready() -> None:
    response = client.get("/ready")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["ready"] is True
    assert body["vector_store_ready"] is True
    assert body["retrieval_ready"] is True
    assert body["indexing_ready"] is True
    assert body["profile_ready"] is True
