import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app


client = TestClient(app)


def test_metrics() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["collection"] == "homelab_bootstrap"
    assert body["ready"] is True
    assert body["vector_store_ready"] is True
    assert "hybrid" in body["retrieval_modes"]
    assert "incremental_updates" in body["indexed_features"]
