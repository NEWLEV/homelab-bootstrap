import math
import re
from typing import Any


VECTOR_WEIGHT = 0.45
LEXICAL_WEIGHT = 0.55
MIN_CANDIDATES = 20
CANDIDATE_MULTIPLIER = 4
MAX_CANDIDATES = 80

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._:/-][a-z0-9]+)*")


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def tokenize(value: str) -> tuple[str, ...]:
    return tuple(TOKEN_PATTERN.findall(value.casefold()))


def matching_tokens(
    query: str,
    candidate: dict[str, Any],
) -> list[str]:
    query_tokens = set(tokenize(query))
    candidate_text = " ".join(
        str(candidate.get(field, ""))
        for field in ("snippet", "path", "filename", "directory")
    )
    return sorted(query_tokens & set(tokenize(candidate_text)))




def lexical_score(query: str, candidate: dict[str, Any]) -> float:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return 0.0

    snippet = normalize_text(str(candidate.get("snippet", "")))
    path = normalize_text(str(candidate.get("path", "")))
    filename = normalize_text(str(candidate.get("filename", "")))
    directory = normalize_text(str(candidate.get("directory", "")))

    if normalized_query in {filename, path}:
        return 1.0

    if path.endswith(f"/{normalized_query}"):
        return 1.0

    scores: list[float] = []

    if normalized_query in snippet:
        scores.append(0.95)

    metadata_text = " ".join((path, filename, directory))
    if normalized_query in metadata_text:
        scores.append(0.90)

    query_tokens = set(tokenize(normalized_query))
    if query_tokens:
        candidate_tokens = set(
            tokenize(" ".join((snippet, metadata_text)))
        )
        coverage = len(query_tokens & candidate_tokens) / len(query_tokens)
        scores.append(0.80 * coverage)

    return max(scores, default=0.0)


def normalize_vector_scores(
    candidates: list[dict[str, Any]],
) -> list[float]:
    distances = [
        float(candidate.get("distance", math.inf))
        for candidate in candidates
    ]
    finite_distances = [
        distance
        for distance in distances
        if math.isfinite(distance)
    ]

    if not finite_distances:
        return [0.0] * len(candidates)

    minimum = min(finite_distances)
    maximum = max(finite_distances)

    if minimum == maximum:
        return [
            1.0 if math.isfinite(distance) else 0.0
            for distance in distances
        ]

    span = maximum - minimum
    return [
        (maximum - distance) / span
        if math.isfinite(distance)
        else 0.0
        for distance in distances
    ]


def candidate_pool_size(limit: int, collection_size: int) -> int:
    desired = min(
        MAX_CANDIDATES,
        max(MIN_CANDIDATES, limit * CANDIDATE_MULTIPLIER),
    )
    return min(desired, collection_size)


def candidate_identity(candidate: dict[str, Any]) -> tuple[Any, ...]:
    record_id = candidate.get("id")
    if record_id:
        return ("id", str(record_id))

    return (
        "source",
        str(candidate.get("path", "")),
        int(candidate.get("line_start", 0)),
        int(candidate.get("line_end", 0)),
        str(candidate.get("snippet", "")),
    )


def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    limit: int,
    debug: bool = False,
) -> list[dict[str, Any]]:
    vector_scores = normalize_vector_scores(candidates)
    ranked: list[dict[str, Any]] = []

    for candidate, vector_score in zip(
        candidates,
        vector_scores,
        strict=True,
    ):
        lexical = lexical_score(query, candidate)
        matches = matching_tokens(query, candidate)
        ranked.append(
            {
                **candidate,
                "_vector_score": vector_score,
                "_lexical_score": lexical,
                "_matching_tokens": matches,
                "_combined_score": (
                    VECTOR_WEIGHT * vector_score
                    + LEXICAL_WEIGHT * lexical
                ),
            }
        )

    ranked.sort(
        key=lambda candidate: (
            -candidate["_combined_score"],
            -candidate["_lexical_score"],
            float(candidate.get("distance", math.inf)),
            str(candidate.get("path", "")),
            int(candidate.get("line_start", 0)),
            int(candidate.get("line_end", 0)),
            str(candidate.get("id", "")),
        )
    )

    unique: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for candidate in ranked:
        identity = candidate_identity(candidate)
        if identity in seen:
            continue

        seen.add(identity)
        result = {
            key: value
            for key, value in candidate.items()
            if not key.startswith("_") and key != "id"
        }

        if debug:
            result.update(
                {
                    "vector_score": candidate["_vector_score"],
                    "lexical_score": candidate["_lexical_score"],
                    "combined_score": candidate["_combined_score"],
                    "matching_tokens": candidate["_matching_tokens"],
                    "rank": len(unique) + 1,
                }
            )

        unique.append(result)

        if len(unique) == limit:
            break

    return unique
