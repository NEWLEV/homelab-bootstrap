import pytest

from app.confidence import (
    assess_citation_completeness,
    assess_retrieval_confidence,
    claim_segments,
    sigmoid,
)


def result(**overrides) -> dict:
    value = {
        "path": "docs.md",
        "line_start": 1,
        "line_end": 5,
        "combined_score": 0.6,
        "matching_tokens": ["backups", "run"],
        "reranker_used": True,
        "reranker_score": 1.0,
    }
    value.update(overrides)
    return value


def test_reranker_confidence_accepts_grounded_result() -> None:
    assessment = assess_retrieval_confidence(
        "When do backups run?",
        [result()],
    )

    assert assessment.sufficient is True
    assert assessment.score > 0.7
    assert assessment.token_coverage == 1.0
    assert assessment.reasons == ()


def test_low_reranker_score_rejects_unrelated_result() -> None:
    assessment = assess_retrieval_confidence(
        "What color is the moon base cafeteria?",
        [
            result(
                matching_tokens=[],
                reranker_score=-11.0,
                combined_score=0.3,
            )
        ],
    )

    assert assessment.sufficient is False
    assert assessment.score < 0.01
    assert set(assessment.reasons) == {
        "low_relevance",
        "low_token_coverage",
        "below_confidence_threshold",
    }


def test_hybrid_fallback_uses_combined_score() -> None:
    assessment = assess_retrieval_confidence(
        "Which port publishes local-rag-api?",
        [
            result(
                reranker_used=False,
                reranker_score=None,
                combined_score=0.6,
                matching_tokens=["local-rag-api"],
            )
        ],
    )

    assert assessment.sufficient is True
    assert assessment.relevance == 0.6


def test_no_results_are_rejected() -> None:
    assessment = assess_retrieval_confidence("query", [])

    assert assessment.sufficient is False
    assert assessment.score == 0.0
    assert "no_results" in assessment.reasons


@pytest.mark.parametrize("minimum", [-0.1, 1.1])
def test_invalid_minimum_is_rejected(minimum: float) -> None:
    with pytest.raises(ValueError):
        assess_retrieval_confidence("query", [result()], minimum=minimum)


def test_sigmoid_is_stable_for_extreme_scores() -> None:
    assert sigmoid(1000.0) == 1.0
    assert sigmoid(-1000.0) == 0.0


def test_all_claims_with_valid_citations_are_complete() -> None:
    answer = (
        "Backups run nightly. [docs.md:1-5] "
        "Retention is seven days [docs.md:1-5]."
    )

    assessment = assess_citation_completeness(answer, [result()])

    assert assessment.complete is True
    assert assessment.completeness == 1.0
    assert assessment.reasons == ()


def test_uncited_claim_is_rejected() -> None:
    answer = (
        "Backups run nightly. [docs.md:1-5] "
        "Retention is seven days."
    )

    assessment = assess_citation_completeness(answer, [result()])

    assert assessment.complete is False
    assert assessment.completeness == 0.5
    assert assessment.reasons == ("incomplete_citations",)


def test_invalid_citation_is_rejected() -> None:
    assessment = assess_citation_completeness(
        "Backups run nightly. [invented.md:1-2]",
        [result()],
    )

    assert assessment.complete is False
    assert "invalid_citation" in assessment.reasons


def test_missing_citation_is_rejected() -> None:
    assessment = assess_citation_completeness(
        "Backups run nightly.",
        [result()],
    )

    assert assessment.complete is False
    assert set(assessment.reasons) == {
        "missing_citations",
        "incomplete_citations",
    }


def test_citation_after_period_attaches_to_preceding_claim() -> None:
    segments = claim_segments("Backups run nightly. [docs.md:1-5]")

    assert segments == ["Backups run nightly CITATION"]
