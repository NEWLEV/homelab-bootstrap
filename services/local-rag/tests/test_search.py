from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


class FakeCollection:
    name = "homelab_bootstrap"

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.query_arguments: dict[str, Any] = {}

    def count(self) -> int:
        return 100

    def query(self, **kwargs) -> dict[str, list[list[Any]]]:
        self.query_arguments = kwargs
        return {
            "ids": [[record["id"] for record in self.records]],
            "documents": [[record["snippet"] for record in self.records]],
            "metadatas": [[record["metadata"] for record in self.records]],
            "distances": [[record["distance"] for record in self.records]],
        }


def record(
    record_id: str,
    *,
    path: str = "compose/ai/local-rag.yml",
    directory: str = "compose/ai",
    filename: str = "local-rag.yml",
    extension: str = ".yml",
    snippet: str = "OLLAMA_URL: http://ollama:11434",
    distance: float = 0.2,
    line_start: int = 10,
    line_end: int = 20,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "snippet": snippet,
        "distance": distance,
        "metadata": {
            "path": path,
            "directory": directory,
            "filename": filename,
            "extension": extension,
            "line_start": line_start,
            "line_end": line_end,
        },
    }


def configure_retrieval(monkeypatch, records) -> FakeCollection:
    collection = FakeCollection(records)
    monkeypatch.setattr(main, "collection", collection)
    monkeypatch.setattr(main, "embed_text", lambda query: [0.1, 0.2])
    return collection


@pytest.mark.parametrize(
    ("payload", "expected_where"),
    [
        (
            {"path": "compose/ai/local-rag.yml"},
            {"path": {"$eq": "compose/ai/local-rag.yml"}},
        ),
        (
            {"path_prefix": "compose/ai"},
            None,
        ),
        (
            {"directory": "compose/ai"},
            {"directory": {"$eq": "compose/ai"}},
        ),
        (
            {"extension": ".yml"},
            {"extension": {"$eq": ".yml"}},
        ),
    ],
)
def test_search_passes_metadata_filters(
    monkeypatch,
    payload,
    expected_where,
) -> None:
    collection = configure_retrieval(monkeypatch, [record("one")])
    response = client.post(
        "/search",
        json={"query": "OLLAMA_URL", **payload},
    )
    assert response.status_code == 200
    assert collection.query_arguments.get("where") == expected_where
    assert response.json()["results"][0]["path"] == (
        "compose/ai/local-rag.yml"
    )


def test_search_without_filters_is_backward_compatible(monkeypatch) -> None:
    collection = configure_retrieval(monkeypatch, [record("one")])
    response = client.post(
        "/search",
        json={"query": "model endpoint", "limit": 2},
    )
    assert response.status_code == 200
    assert "where" not in collection.query_arguments
    assert collection.query_arguments["n_results"] == 20

    result = response.json()["results"][0]
    assert result["distance"] == 0.2
    assert result["line_start"] == 10
    assert result["line_end"] == 20
    assert "id" not in result
    assert all(not key.startswith("_") for key in result)


def test_path_prefix_rejects_substring_false_positive(monkeypatch) -> None:
    configure_retrieval(
        monkeypatch,
        [
            record("match"),
            record(
                "false-positive",
                path="archive/compose/ai/old.yml",
                directory="archive/compose/ai",
                filename="old.yml",
            ),
        ],
    )
    response = client.post(
        "/search",
        json={
            "query": "OLLAMA_URL",
            "path_prefix": "compose/ai",
        },
    )
    assert response.status_code == 200
    assert [item["path"] for item in response.json()["results"]] == [
        "compose/ai/local-rag.yml"
    ]


def test_search_rejects_blank_query() -> None:
    response = client.post("/search", json={"query": "   "})
    assert response.status_code == 422


def test_search_and_ask_limits_remain_enforced() -> None:
    assert client.post(
        "/search",
        json={"query": "test", "limit": 21},
    ).status_code == 422
    assert client.post(
        "/ask",
        json={"question": "test", "limit": 11},
    ).status_code == 422


def test_ask_passes_filters_and_preserves_citation_metadata(
    monkeypatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_retrieve(query, limit, **kwargs):
        calls.append(kwargs)
        return [
            {
                "path": "compose/ai/local-rag.yml",
                "directory": "compose/ai",
                "filename": "local-rag.yml",
                "extension": ".yml",
                "line_start": 10,
                "line_end": 20,
                "distance": 0.1,
                "snippet": "The service is local-rag-api.",
                "combined_score": 0.8,
                "matching_tokens": ["service", "name"],
                "reranker_used": False,
            }
        ]

    monkeypatch.setattr(main, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda prompt: (
            "The service is local-rag-api. "
            "[compose/ai/local-rag.yml:10-20]"
        ),
    )

    response = client.post(
        "/ask",
        json={
            "question": "What is the service name?",
            "path": "compose/ai/local-rag.yml",
            "path_prefix": "compose/ai",
            "directory": "compose/ai",
            "extension": ".yml",
        },
    )
    assert response.status_code == 200
    assert calls == [
        {
            "debug": True,
            "path": "compose/ai/local-rag.yml",
            "path_prefix": "compose/ai",
            "directory": "compose/ai",
            "extension": ".yml",
        }
    ]
    assert response.json()["citations"] == [
        {
            "path": "compose/ai/local-rag.yml",
            "line_start": 10,
            "line_end": 20,
            "distance": 0.1,
        }


    ]

def test_search_debug_exposes_retrieval_diagnostics(monkeypatch) -> None:
    configure_retrieval(monkeypatch, [record("one")])
    response = client.post(
        "/search",
        json={"query": "OLLAMA_URL", "debug": True},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["rank"] == 1
    assert result["matching_tokens"] == ["ollama_url"]
    assert result["hybrid_rank"] == 1
    assert result["reranker_used"] is False
    assert set(result) >= {
        "vector_score",
        "lexical_score",
        "combined_score",
    }


def test_ask_debug_exposes_typed_retrieval_diagnostics(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [
            {
                "path": "compose/ai/local-rag.yml",
                "line_start": 10,
                "line_end": 20,
                "distance": 0.1,
                "snippet": "The service is local-rag-api.",
                "vector_score": 0.9,
                "lexical_score": 0.95,
                "combined_score": 0.9275,
                "matching_tokens": ["local-rag-api"],
                "rank": 1,
            }
        ],
    )
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda prompt: (
            "The service is local-rag-api. "
            "[compose/ai/local-rag.yml:10-20]"
        ),
    )

    response = client.post(
        "/ask",
        json={
            "question": "local-rag-api",
            "debug": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["retrieval_debug"] == [
        {
            "path": "compose/ai/local-rag.yml",
            "line_start": 10,
            "line_end": 20,
            "distance": 0.1,
            "vector_score": 0.9,
            "lexical_score": 0.95,
            "combined_score": 0.9275,
            "matching_tokens": ["local-rag-api"],
            "rank": 1,
            "reranker_used": False,
        }
    ]
    assert response.json()["confidence"] == 0.942
    assert response.json()["citation_completeness"] == 1.0


def confident_match() -> dict[str, Any]:
    return {
        "path": "compose/ai/local-rag.yml",
        "line_start": 10,
        "line_end": 20,
        "distance": 0.1,
        "snippet": "Backups run nightly.",
        "vector_score": 0.9,
        "lexical_score": 0.9,
        "combined_score": 0.9,
        "matching_tokens": ["backups", "run"],
        "rank": 1,
        "reranker_used": False,
    }


def test_ask_low_confidence_skips_generation(monkeypatch) -> None:
    match = confident_match()
    match.update(
        combined_score=0.05,
        matching_tokens=[],
    )
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [match],
    )

    def fail_generation(prompt: str) -> str:
        raise AssertionError("generation must be skipped")

    monkeypatch.setattr(main, "generate_answer", fail_generation)

    response = client.post(
        "/ask",
        json={
            "question": "What color is the moon base cafeteria?",
            "debug": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["confidence"] < 0.45
    assert "below_confidence_threshold" in body["confidence_reasons"]


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ("Backups run nightly.", "missing_citations"),
        (
            "Backups run nightly. [unknown.md:1-2]",
            "invalid_citation",
        ),
        (
            "Backups run nightly. A report is emailed. "
            "[compose/ai/local-rag.yml:10-20]",
            "incomplete_citations",
        ),
    ],
)
def test_ask_refuses_incomplete_or_invalid_citations(
    monkeypatch,
    answer: str,
    reason: str,
) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [confident_match()],
    )
    monkeypatch.setattr(main, "generate_answer", lambda prompt: answer)

    response = client.post(
        "/ask",
        json={"question": "When do backups run?", "debug": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert reason in body["confidence_reasons"]
    assert body["citations"] == []


def test_ask_grounded_response_reports_confidence(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [confident_match()],
    )
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda prompt: (
            "Backups run nightly. "
            "[compose/ai/local-rag.yml:10-20]"
        ),
    )

    response = client.post(
        "/ask",
        json={"question": "When do backups run?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["confidence"] == 0.92
    assert body["citation_completeness"] == 1.0
    assert "confidence_reasons" not in body
