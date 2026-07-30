import math
import re
from dataclasses import dataclass
from typing import Any

from app.retrieval import tokenize


DEFAULT_MIN_CONFIDENCE = 0.45
RELEVANCE_WEIGHT = 0.8
TOKEN_COVERAGE_WEIGHT = 0.2
LOW_RELEVANCE = 0.5
LOW_TOKEN_COVERAGE = 0.2

STOPWORDS = {
    "a",
    "an",
    "are",
    "do",
    "does",
    "how",
    "is",
    "the",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}

CITATION_PATTERN = re.compile(r"\[([^:\]\n]+):(\d+)-(\d+)\]")
CLAIM_SEPARATOR = re.compile(r"[.!?\n]+")
TRAILING_CITATIONS = re.compile(
    r"([.!?])(\s+CITATION\b(?:\s+CITATION\b)*)"
)


@dataclass(frozen=True)
class ConfidenceAssessment:
    score: float
    sufficient: bool
    relevance: float
    token_coverage: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CitationAssessment:
    completeness: float
    complete: bool
    reasons: tuple[str, ...]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        factor = math.exp(-value)
        return 1.0 / (1.0 + factor)
    factor = math.exp(value)
    return factor / (1.0 + factor)


def significant_tokens(query: str) -> set[str]:
    tokens = set(tokenize(query))
    significant = tokens - STOPWORDS
    return significant or tokens


def result_relevance(result: dict[str, Any]) -> float:
    if result.get("reranker_used") and result.get("reranker_score") is not None:
        return sigmoid(float(result["reranker_score"]))
    return clamp(float(result.get("combined_score", 0.0)))


def result_token_coverage(query: str, result: dict[str, Any]) -> float:
    query_tokens = significant_tokens(query)
    if not query_tokens:
        return 0.0
    matched = set(result.get("matching_tokens", ())) & query_tokens
    return len(matched) / len(query_tokens)


def assess_retrieval_confidence(
    query: str,
    results: list[dict[str, Any]],
    *,
    minimum: float = DEFAULT_MIN_CONFIDENCE,
) -> ConfidenceAssessment:
    if not 0.0 <= minimum <= 1.0:
        raise ValueError("minimum confidence must be between 0 and 1")

    if not results:
        return ConfidenceAssessment(
            score=0.0,
            sufficient=False,
            relevance=0.0,
            token_coverage=0.0,
            reasons=("no_results", "below_confidence_threshold"),
        )

    top_result = results[0]
    relevance = result_relevance(top_result)
    coverage = result_token_coverage(query, top_result)
    score = clamp(
        RELEVANCE_WEIGHT * relevance
        + TOKEN_COVERAGE_WEIGHT * coverage
    )
    reasons: list[str] = []

    if relevance < LOW_RELEVANCE:
        reasons.append("low_relevance")
    if coverage < LOW_TOKEN_COVERAGE:
        reasons.append("low_token_coverage")
    if score < minimum:
        reasons.append("below_confidence_threshold")

    return ConfidenceAssessment(
        score=round(score, 6),
        sufficient=score >= minimum,
        relevance=round(relevance, 6),
        token_coverage=round(coverage, 6),
        reasons=tuple(reasons),
    )


def citation_keys(answer: str) -> list[tuple[str, int, int]]:
    return [
        (path, int(line_start), int(line_end))
        for path, line_start, line_end in CITATION_PATTERN.findall(answer)
    ]


def valid_citation_keys(
    results: list[dict[str, Any]],
) -> set[tuple[str, int, int]]:
    return {
        (
            str(result.get("path", "")),
            int(result.get("line_start", 0)),
            int(result.get("line_end", 0)),
        )
        for result in results
    }


def claim_segments(answer: str) -> list[str]:
    normalized = CITATION_PATTERN.sub(" CITATION ", answer)
    normalized = TRAILING_CITATIONS.sub(r"\2\1", normalized)
    return [
        " ".join(segment.split())
        for segment in CLAIM_SEPARATOR.split(normalized)
        if re.search(r"[A-Za-z0-9]", segment.replace("CITATION", ""))
    ]


def assess_citation_completeness(
    answer: str,
    results: list[dict[str, Any]],
) -> CitationAssessment:
    cited = citation_keys(answer)
    valid = valid_citation_keys(results)
    reasons: list[str] = []

    if not cited:
        reasons.append("missing_citations")
    if any(key not in valid for key in cited):
        reasons.append("invalid_citation")

    claims = claim_segments(answer)
    cited_claims = sum("CITATION" in claim for claim in claims)
    completeness = cited_claims / len(claims) if claims else 0.0
    if completeness < 1.0:
        reasons.append("incomplete_citations")

    return CitationAssessment(
        completeness=round(completeness, 6),
        complete=not reasons,
        reasons=tuple(reasons),
    )
