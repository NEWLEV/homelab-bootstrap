from __future__ import annotations

import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app

client = TestClient(app)


def test_platform_runbook_endpoint_exposes_safe_commands() -> None:
    response = client.get("/platform/runbook")

    assert response.status_code == 200
    assert "Aisha Runbook" in response.text
    assert "systemctl --user start aisha-local-rag.service" in response.text
    assert "/docs" in response.text


def test_platform_web_dashboard_endpoint_exposes_read_only_controls() -> None:
    response = client.get("/platform/web-dashboard")

    assert response.status_code == 200

    body = response.text

    assert "Runbook" in body
    assert "API Docs" in body
    assert "/platform/runbook" in body
    assert "systemctl --user status aisha-local-rag.service" in body
    assert "./scripts/install-local-rag-service.sh" in body


def test_root_redirects_to_dashboard() -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/platform/web-dashboard"
