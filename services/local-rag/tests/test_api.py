from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["version"] == "0.8.0"
    assert body["vector_store"] == "chromadb"
    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert body["reranker_enabled"] is False
    assert body["reranker_model"] == "Xenova/ms-marco-MiniLM-L-6-v2"
    assert body["reranker_threads"] == 2
    assert body["confidence_min_score"] == 0.45


def test_stats() -> None:
    response = client.get("/stats")

    assert response.status_code == 200

    body = response.json()

    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert isinstance(body["sample_ids"], list)
    assert isinstance(body["sample_paths"], list)
