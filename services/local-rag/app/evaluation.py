from typing import Any


def reciprocal_rank(
    result_paths: list[str],
    expected_paths: set[str],
) -> float:
    for rank, path in enumerate(result_paths, start=1):
        if path in expected_paths:
            return 1.0 / rank
    return 0.0


def calculate_metrics(
    evaluations: list[dict[str, Any]],
) -> dict[str, float | int]:
    case_count = len(evaluations)
    if case_count == 0:
        return {
            "cases": 0,
            "top_1_accuracy": 0.0,
            "top_k_recall": 0.0,
            "mean_reciprocal_rank": 0.0,
        }

    top_1_hits = 0
    top_k_hits = 0
    reciprocal_rank_total = 0.0

    for evaluation in evaluations:
        expected_paths = set(evaluation["expected_paths"])
        result_paths = list(evaluation["result_paths"])
        rank_score = reciprocal_rank(result_paths, expected_paths)

        if result_paths and result_paths[0] in expected_paths:
            top_1_hits += 1
        if rank_score > 0:
            top_k_hits += 1
        reciprocal_rank_total += rank_score

    return {
        "cases": case_count,
        "top_1_accuracy": top_1_hits / case_count,
        "top_k_recall": top_k_hits / case_count,
        "mean_reciprocal_rank": reciprocal_rank_total / case_count,
    }
