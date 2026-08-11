from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_rag_n8n_export_keeps_credentials_out_of_source() -> None:
    workflow = json.loads(
        (REPO_ROOT / "scripts" / "local_rag_grounded_lookup_n8n_export.json").read_text(
            encoding="utf-8"
        )
    )
    request = next(node for node in workflow["nodes"] if node["id"] == "query-local-rag")

    assert workflow["name"] == "local-rag-grounded-lookup"
    assert workflow["id"] == "aisha-local-rag-grounded-lookup"
    assert workflow["active"] is False
    assert request["parameters"]["url"] == "http://local-rag-api:8080/ask"
    assert request["parameters"]["authentication"] == "genericCredentialType"
    assert "Bearer <token>" in request["notes"]
    assert "credentials" not in request


def test_n8n_compose_reaches_local_rag_and_has_a_healthcheck() -> None:
    compose = (REPO_ROOT / "compose" / "automation" / "n8n.yml").read_text(encoding="utf-8")

    assert "local-rag_rag-private" in compose
    assert "http://127.0.0.1:5678/healthz" in compose

def test_tailnet_router_preserves_n8n_base_path() -> None:
    router = (REPO_ROOT / "configs" / "tailnet-router" / "Caddyfile").read_text(
        encoding="utf-8"
    )

    assert "handle /n8n/*" in router
    assert "handle_path /n8n/*" not in router