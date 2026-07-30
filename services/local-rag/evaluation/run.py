import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.evaluation import calculate_metrics


DEFAULT_CASES = Path("/app/evaluation/cases.json")


def post_search(
    api_url: str,
    query: str,
    limit: int,
) -> list[str]:
    payload = json.dumps(
        {
            "query": query,
            "limit": limit,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.load(response)
    return [result["path"] for result in body.get("results", [])]


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        cases = json.load(source)
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation cases must be a non-empty list.")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Local RAG retrieval against repository cases."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8080")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-top-1", type=float)
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-mrr", type=float)
    args = parser.parse_args()

    if args.top_k < 1 or args.top_k > 20:
        parser.error("--top-k must be between 1 and 20")

    cases = load_cases(args.cases)
    evaluations: list[dict[str, Any]] = []

    try:
        for case in cases:
            result_paths = post_search(
                args.api_url,
                case["query"],
                args.top_k,
            )
            evaluations.append(
                {
                    "name": case["name"],
                    "query": case["query"],
                    "expected_paths": case["expected_paths"],
                    "result_paths": result_paths,
                }
            )
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Evaluation request failed: {exc}", file=sys.stderr)
        return 2

    metrics = calculate_metrics(evaluations)
    report = {
        "top_k": args.top_k,
        "metrics": metrics,
        "cases": evaluations,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    thresholds = (
        ("top_1_accuracy", args.min_top_1),
        ("top_k_recall", args.min_recall),
        ("mean_reciprocal_rank", args.min_mrr),
    )
    failed = [
        name
        for name, minimum in thresholds
        if minimum is not None and metrics[name] < minimum
    ]
    if failed:
        print(
            "Evaluation thresholds failed: " + ", ".join(failed),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
