from fastapi.testclient import TestClient

import app.main as main
from app.auth import BearerTokenAuth


TOKEN = "b" * 64
client = TestClient(main.app)


def enable_auth(monkeypatch) -> None:
    monkeypatch.setattr(main, "api_auth", BearerTokenAuth(TOKEN))


def test_health_remains_public_when_auth_is_enabled(monkeypatch) -> None:
    enable_auth(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["authentication_enabled"] is True


def test_protected_endpoint_requires_bearer_token(monkeypatch) -> None:
    enable_auth(monkeypatch)

    response = client.get("/metrics")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_authentication_scheme_is_rejected(monkeypatch) -> None:
    enable_auth(monkeypatch)

    response = client.get(
        "/metrics",
        headers={"Authorization": f"Basic {TOKEN}"},
    )

    assert response.status_code == 401


def test_matching_bearer_token_allows_request(monkeypatch) -> None:
    enable_auth(monkeypatch)

    response = client.get(
        "/metrics",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    assert response.status_code == 200
    assert "counters" in response.json()


def test_documentation_and_schema_are_protected(monkeypatch) -> None:
    enable_auth(monkeypatch)

    docs = client.get("/docs")
    schema = client.get("/openapi.json")

    assert docs.status_code == 401
    assert schema.status_code == 401


def test_disabled_auth_preserves_existing_behavior(monkeypatch) -> None:
    monkeypatch.setattr(main, "api_auth", BearerTokenAuth())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert main.api_auth.enabled is False
