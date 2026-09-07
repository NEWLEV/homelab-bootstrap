import httpx
import pytest
from fastapi.testclient import TestClient

import app.indexer as indexer
import app.main as main
from app.metrics import MetricRegistry, metrics
from app.index_jobs import IndexJobManager


def test_metric_registry_reports_stable_zero_values() -> None:
    registry = MetricRegistry()

    result = registry.snapshot()

    assert result["counters"]["grounded_answers"] == 0
    assert result["counters"]["refused_answers"] == 0
    assert result["counters"]["dependency_failures"] == 0
    assert result["dependency_failures"]["embedding"] == 0
    assert result["latencies_ms"]["retrieval"] == {
        "count": 0,
        "total_ms": 0.0,
        "average_ms": 0.0,
        "last_ms": 0.0,
        "max_ms": 0.0,
    }


def test_metric_registry_aggregates_timings() -> None:
    registry = MetricRegistry()

    registry.observe("retrieval", 0.1)
    registry.observe("retrieval", 0.3)

    timing = registry.snapshot()["latencies_ms"]["retrieval"]
    assert timing == {
        "count": 2,
        "total_ms": 400.0,
        "average_ms": 200.0,
        "last_ms": 300.0,
        "max_ms": 300.0,
    }


def test_dependency_failure_updates_total_and_component() -> None:
    registry = MetricRegistry()

    registry.dependency_failure("generation")
    registry.dependency_failure("generation")

    result = registry.snapshot()
    assert result["counters"]["dependency_failures"] == 2
    assert result["dependency_failures"]["generation"] == 2


def test_reset_clears_recorded_values() -> None:
    registry = MetricRegistry()
    registry.increment("grounded_answers")
    registry.observe("generation", 0.2)

    registry.reset()

    result = registry.snapshot()
    assert result["counters"]["grounded_answers"] == 0
    assert result["latencies_ms"]["generation"]["count"] == 0


def test_retrieval_wrapper_records_latency(monkeypatch) -> None:
    before = metrics.snapshot()["latencies_ms"]["retrieval"]["count"]
    monkeypatch.setattr(main, "_retrieve_chunks", lambda **kwargs: [])

    assert main.retrieve_chunks("query", 5) == []

    after = metrics.snapshot()["latencies_ms"]["retrieval"]["count"]
    assert after == before + 1


def test_embedding_failure_records_latency_and_dependency(
    monkeypatch,
) -> None:
    before = metrics.snapshot()

    def fail_post(*args, **kwargs):
        raise httpx.ConnectError("embedding offline")

    monkeypatch.setattr(main.httpx, "post", fail_post)

    with pytest.raises(httpx.ConnectError):
        main.embed_text("query")

    after = metrics.snapshot()
    assert (
        after["latencies_ms"]["embedding"]["count"]
        == before["latencies_ms"]["embedding"]["count"] + 1
    )
    assert (
        after["dependency_failures"]["embedding"]
        == before["dependency_failures"]["embedding"] + 1
    )


def test_generation_success_records_latency(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"response": "Grounded answer."}

    before = metrics.snapshot()
    monkeypatch.setattr(
        main.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse(),
    )

    answer = main.generate_answer("prompt", model=main.GENERATION_MODEL)

    after = metrics.snapshot()
    assert answer == "Grounded answer."
    assert (
        after["latencies_ms"]["generation"]["count"]
        == before["latencies_ms"]["generation"]["count"] + 1
    )
    assert (
        after["dependency_failures"]["generation"]
        == before["dependency_failures"]["generation"]
    )


def test_ask_records_grounded_and_refused_outcomes(monkeypatch) -> None:
    client = TestClient(main.app)
    match = {
        "path": "docs.md",
        "line_start": 10,
        "line_end": 20,
        "distance": 0.1,
        "snippet": "Backups run nightly.",
        "combined_score": 0.9,
        "matching_tokens": ["backups", "run"],
        "reranker_used": False,
    }
    answers = iter(
        [
            "Backups run nightly. [docs.md:10-20]",
            "INSUFFICIENT_CONTEXT",
        ]
    )
    monkeypatch.setattr(
        main,
        "retrieve_chunks",
        lambda query, limit, **kwargs: [match],
    )
    monkeypatch.setattr(
        main,
        "generate_answer",
        lambda prompt, *, model: next(answers),
    )
    before = metrics.snapshot()["counters"]

    grounded = client.post(
        "/ask",
        json={"question": "When do backups run?"},
    )
    refused = client.post(
        "/ask",
        json={"question": "When do backups run?"},
    )

    after = metrics.snapshot()["counters"]
    assert grounded.json()["grounded"] is True
    assert refused.json()["grounded"] is False
    assert after["ask_requests"] == before["ask_requests"] + 2
    assert (
        after["grounded_answers"]
        == before["grounded_answers"] + 1
    )
    assert (
        after["refused_answers"]
        == before["refused_answers"] + 1
    )


def test_failed_index_records_duration_and_dependency(
    monkeypatch,
    tmp_path,
) -> None:
    client = TestClient(main.app)
    monkeypatch.setattr(
        main,
        "index_job_manager",
        IndexJobManager(tmp_path / "index-status.json"),
    )

    def fail_index(**kwargs):
        raise RuntimeError("embedding unavailable")

    monkeypatch.setattr(indexer, "index_repository", fail_index)
    before = metrics.snapshot()

    response = client.post("/index")

    after = metrics.snapshot()
    assert response.status_code == 500
    assert (
        after["counters"]["index_requests"]
        == before["counters"]["index_requests"] + 1
    )
    assert (
        after["latencies_ms"]["indexing"]["count"]
        == before["latencies_ms"]["indexing"]["count"] + 1
    )
    assert (
        after["dependency_failures"]["indexing"]
        == before["dependency_failures"]["indexing"] + 1
    )
    assert (
        after["counters"]["dependency_failures"]
        == before["counters"]["dependency_failures"] + 1
    )
