from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["version"] == "0.9.2"
    assert body["vector_store"] == "chromadb"
    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert body["reranker_enabled"] is False
    assert body["reranker_model"] == "Xenova/ms-marco-MiniLM-L-6-v2"
    assert body["reranker_threads"] == 2
    assert body["confidence_min_score"] == 0.45
    assert body["index_status"] in {"idle", "failed"}
    assert "last_index_success_at" in body
    assert body["index_schema_version"] == "1"


def test_index_integrity() -> None:
    response = client.get("/index/integrity")

    assert response.status_code == 200

    body = response.json()
    assert body["valid"] is True
    assert body["reindex_required"] is False
    assert body["invalid_records"] == 0
    assert body["schema_version"] == "1"
    assert body["collection_schema_version"] == "1"
    assert body["embedding_model"] == "nomic-embed-text"


def test_stats() -> None:
    response = client.get("/stats")

    assert response.status_code == 200

    body = response.json()

    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert isinstance(body["sample_ids"], list)
    assert isinstance(body["sample_paths"], list)
