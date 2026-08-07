import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))
os.environ["EMBEDDING_PROFILE"] = "accurate"
os.environ["GENERATION_PROFILE"] = "compact"

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app


client = TestClient(app)


def test_status() -> None:
    response = client.get("/status")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["vector_store"] == "chromadb"
    assert body["collection"] == "homelab_bootstrap"
    assert body["embedding_profile"] == "accurate"
    assert body["generation_profile"] == "compact"
    assert body["generation_options"] == {"temperature": 0.2, "max_tokens": 256, "top_p": 0.8}
    assert body["embedding_model_fallbacks"] == ["nomic-embed-text", "all-MiniLM-L6-v2"]
    assert "hybrid" in body["retrieval_modes"]
