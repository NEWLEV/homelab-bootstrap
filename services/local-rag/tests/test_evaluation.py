from app.evaluation import calculate_metrics, reciprocal_rank


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(
        ["wrong.md", "expected.md"],
        {"expected.md"},
    ) == 0.5
    assert reciprocal_rank(["wrong.md"], {"expected.md"}) == 0.0


def test_calculate_metrics() -> None:
    metrics = calculate_metrics(
        [
            {
                "expected_paths": ["a.md"],
                "result_paths": ["a.md", "b.md"],
            },
            {
                "expected_paths": ["c.md"],
                "result_paths": ["x.md", "c.md"],
            },
            {
                "expected_paths": ["missing.md"],
                "result_paths": ["x.md", "y.md"],
            },
        ]
    )

    assert metrics == {
        "cases": 3,
        "top_1_accuracy": 1 / 3,
        "top_k_recall": 2 / 3,
        "mean_reciprocal_rank": 0.5,
    }


def test_calculate_metrics_with_no_cases() -> None:
    assert calculate_metrics([]) == {
        "cases": 0,
        "top_1_accuracy": 0.0,
        "top_k_recall": 0.0,
        "mean_reciprocal_rank": 0.0,
    }
