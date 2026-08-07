import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

import app.main as app_main

app_main = importlib.reload(app_main)
app = app_main.app


client = TestClient(app)


def test_summary() -> None:
    response = client.get("/summary")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert body["collection"] == "homelab_bootstrap"
    assert body["ready"] is True
    assert body["chunks"] >= 0
    assert body["sources"] >= 0
    assert body["grouped_sources"] is None
    assert "hybrid" in body["retrieval_modes"]
    assert "Grouped context" in body["notes"][0]


def test_summary_with_question_groups_sources() -> None:
    response = client.get("/summary", params={"question": "hybrid retrieval"})

    assert response.status_code == 200

    body = response.json()

    assert body["question"] == "hybrid retrieval"
    assert isinstance(body["best_source"], dict)
    assert isinstance(body["best_source_reason"], str)
    assert body["best_source_reason"]
    assert isinstance(body["grouped_sources"], list)
    assert body["sources"] == len(body["grouped_sources"])
    assert all("chunk_count" in source for source in body["grouped_sources"])
    assert all("digest" in source for source in body["grouped_sources"])
    assert all("top_span" in source for source in body["grouped_sources"])
    assert all("note" in source for source in body["grouped_sources"])
    assert all("confidence_reason" in source for source in body["grouped_sources"])
    assert all(source["confidence_reason"] in source["note"] for source in body["grouped_sources"])
    assert all(source["confidence"] in {"high", "medium", "low"} for source in body["grouped_sources"])
    assert body["best_source"]["confidence"] in {"high", "medium", "low"}
    assert isinstance(body["best_source_reason"], str)
    assert body["best_source_reason"]
    assert "Confidence mix" in body["notes"][1]
    assert "cross-document reasoning" in body["notes"][2]
