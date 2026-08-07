import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))
os.environ["EMBEDDING_PROFILE"] = "balanced"
os.environ["GENERATION_PROFILE"] = "balanced"

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app


client = TestClient(app)


def test_capabilities() -> None:
    response = client.get("/capabilities")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["collection"] == "homelab_bootstrap"
    assert body["retrieval"]["modes"] == ["vector", "lexical", "hybrid"]
    assert body["retrieval"]["grounding"]["citation_format"] == "[source.chunk]"
    assert body["indexing"]["incremental_updates"] is True
    assert body["profiles"]["embedding"]["active"] in {"compact", "balanced", "accurate"}
    assert body["profiles"]["generation"]["active"] in {"compact", "balanced", "accurate"}
