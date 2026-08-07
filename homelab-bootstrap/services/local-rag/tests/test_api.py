from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["vector_store"] == "chromadb"
    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)


def test_stats() -> None:
    response = client.get("/stats")

    assert response.status_code == 200

    body = response.json()

    assert body["collection"] == "homelab_bootstrap"
    assert isinstance(body["chunks"], int)
    assert isinstance(body["sample_ids"], list)
    assert isinstance(body["sample_paths"], list)
