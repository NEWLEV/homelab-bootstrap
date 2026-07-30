from app.reranker import (
    LocalReranker,
    apply_scores,
    fallback_results,
    finalize_results,
)


def candidates() -> list[dict]:
    return [
        {
            "path": "first.md",
            "snippet": "first",
            "rank": 1,
            "vector_score": 1.0,
            "lexical_score": 0.1,
            "combined_score": 0.5,
            "matching_tokens": [],
        },
        {
            "path": "second.md",
            "snippet": "second",
            "rank": 2,
            "vector_score": 0.2,
            "lexical_score": 0.9,
            "combined_score": 0.6,
            "matching_tokens": ["second"],
        },
    ]


def test_apply_scores_reorders_candidates() -> None:
    results = apply_scores(candidates(), [0.1, 0.9], 2)

    assert [result["path"] for result in results] == [
        "second.md",
        "first.md",
    ]
    assert [result["rank"] for result in results] == [1, 2]
    assert [result["hybrid_rank"] for result in results] == [2, 1]
    assert results[0]["reranker_used"] is True


def test_apply_scores_rejects_wrong_score_count() -> None:
    try:
        apply_scores(candidates(), [0.1], 2)
    except ValueError as exc:
        assert "unexpected number" in str(exc)
    else:
        raise AssertionError("Expected score count validation to fail.")


def test_disabled_reranker_preserves_hybrid_order() -> None:
    reranker = LocalReranker(
        enabled=False,
        model_name="unused",
        cache_dir="/tmp/unused",
        threads=1,
    )

    results = reranker.rerank(
        "query",
        candidates(),
        2,
        debug=True,
    )

    assert [result["path"] for result in results] == [
        "first.md",
        "second.md",
    ]
    assert all(result["reranker_used"] is False for result in results)


def test_reranker_failure_falls_back(monkeypatch) -> None:
    reranker = LocalReranker(
        enabled=True,
        model_name="missing",
        cache_dir="/tmp/missing",
        threads=1,
    )
    monkeypatch.setattr(
        reranker,
        "_get_encoder",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    results = reranker.rerank(
        "query",
        candidates(),
        2,
        debug=True,
    )

    assert [result["path"] for result in results] == [
        "first.md",
        "second.md",
    ]
    assert results[0]["reranker_used"] is False
    assert results[0]["reranker_error"] == "RuntimeError: offline"


def test_default_results_hide_all_diagnostics() -> None:
    results = fallback_results(candidates(), 1, error=None)
    public = finalize_results(results, debug=False)

    assert public == [
        {
            "path": "first.md",
            "snippet": "first",
        }
    ]
