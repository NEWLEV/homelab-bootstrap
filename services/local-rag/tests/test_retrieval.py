from typing import Any

from app.retrieval import (
    candidate_pool_size,
    lexical_score,
    rerank_candidates,
)


def candidate(
    record_id: str,
    *,
    snippet: str,
    distance: float,
    path: str = "README.md",
    filename: str = "README.md",
    directory: str = "",
) -> dict[str, Any]:
    return {
        "id": record_id,
        "path": path,
        "filename": filename,
        "directory": directory,
        "extension": ".md",
        "line_start": 1,
        "line_end": 5,
        "distance": distance,
        "snippet": snippet,
    }


def test_exact_environment_variable_match() -> None:
    match = candidate(
        "env",
        snippet="OLLAMA_URL: http://ollama:11434",
        distance=0.8,
    )
    assert lexical_score("OLLAMA_URL", match) == 0.95


def test_exact_filename_match() -> None:
    match = candidate(
        "file",
        snippet="service configuration",
        distance=0.8,
        path="compose/ai/local-rag.yml",
        filename="local-rag.yml",
        directory="compose/ai",
    )
    assert lexical_score("local-rag.yml", match) == 1.0


def test_exact_service_name_match() -> None:
    match = candidate(
        "service",
        snippet="container_name: local-rag-api",
        distance=0.8,
    )
    assert lexical_score("local-rag-api", match) == 0.95


def test_semantic_only_results_keep_vector_order() -> None:
    results = rerank_candidates(
        "disaster recovery strategy",
        [
            candidate("weak", snippet="unrelated words", distance=0.8),
            candidate("strong", snippet="nightly archives", distance=0.1),
        ],
        2,
    )
    assert [result["snippet"] for result in results] == [
        "nightly archives",
        "unrelated words",
    ]


def test_exact_lexical_match_outranks_weak_semantic_match() -> None:
    results = rerank_candidates(
        "OLLAMA_URL",
        [
            candidate("semantic", snippet="model endpoint", distance=0.1),
            candidate(
                "exact",
                snippet="OLLAMA_URL=http://ollama",
                distance=0.9,
            ),
        ],
        2,
    )
    assert results[0]["snippet"] == "OLLAMA_URL=http://ollama"


def test_duplicate_candidates_are_removed() -> None:
    duplicate = candidate("same", snippet="duplicate", distance=0.2)
    results = rerank_candidates("duplicate", [duplicate, duplicate], 5)
    assert len(results) == 1


def test_ordering_is_deterministic() -> None:
    candidates = [
        candidate("b", snippet="same", distance=0.5, path="b.md"),
        candidate("a", snippet="same", distance=0.5, path="a.md"),
    ]
    first = rerank_candidates("same", candidates, 2)
    second = rerank_candidates("same", list(reversed(candidates)), 2)
    assert first == second
    assert [result["path"] for result in first] == ["a.md", "b.md"]


def test_candidate_pool_is_bounded() -> None:
    assert candidate_pool_size(1, 100) == 20
    assert candidate_pool_size(20, 100) == 80
    assert candidate_pool_size(20, 7) == 7



def test_debug_output_contains_scores_tokens_and_rank() -> None:
    results = rerank_candidates(
        "OLLAMA_URL",
        [
            candidate(
                "exact",
                snippet="OLLAMA_URL=http://ollama",
                distance=0.4,
            ),
            candidate("other", snippet="model endpoint", distance=0.2),
        ],
        2,
        debug=True,
    )

    assert [result["rank"] for result in results] == [1, 2]
    assert results[0]["matching_tokens"] == ["ollama_url"]
    assert set(results[0]) >= {
        "vector_score",
        "lexical_score",
        "combined_score",
        "matching_tokens",
        "rank",
    }


def test_default_output_omits_diagnostics() -> None:
    result = rerank_candidates(
        "OLLAMA_URL",
        [
            candidate(
                "exact",
                snippet="OLLAMA_URL=http://ollama",
                distance=0.4,
            )
        ],
        1,
    )[0]

    assert "vector_score" not in result
    assert "lexical_score" not in result
    assert "combined_score" not in result
    assert "matching_tokens" not in result
    assert "rank" not in result
