from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["version"] == "0.11.0"
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
    assert body["authentication_enabled"] is False
    assert body["rate_limiting_enabled"] is False
    assert body["rate_limit_requests_per_minute"] == 0
    assert body["rate_limit_burst"] == 10
    assert body["max_concurrent_requests"] == 0
    assert body["max_request_body_bytes"] == 0


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


def test_metrics() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200

    body = response.json()
    assert body["uptime_seconds"] >= 0
    assert isinstance(body["counters"]["grounded_answers"], int)
    assert isinstance(body["counters"]["refused_answers"], int)
    assert isinstance(body["dependency_failures"]["embedding"], int)
    assert body["latencies_ms"]["retrieval"]["count"] >= 0
    assert body["latencies_ms"]["embedding"]["average_ms"] >= 0
    assert body["latencies_ms"]["generation"]["max_ms"] >= 0
    assert body["latencies_ms"]["indexing"]["last_ms"] >= 0


def test_stats() -> None:
    response = client.get("/stats")

    assert response.status_code == 200

    body = response.json()

    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert isinstance(body["sample_ids"], list)
    assert isinstance(body["sample_paths"], list)
