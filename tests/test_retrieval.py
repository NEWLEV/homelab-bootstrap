import os
from pathlib import Path

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

from app.main import build_metadata_filter
from app.retrieval import rerank_candidates


def test_build_metadata_filter_supports_path_prefix() -> None:
    where = build_metadata_filter(path_prefix="docs/")

    assert where == {"path": {"$contains": "docs/"}}


def test_build_metadata_filter_supports_directory_prefix() -> None:
    where = build_metadata_filter(directory_prefix="docs/guides")

    assert where == {"directory": {"$contains": "docs/guides"}}


def test_rerank_candidates_prefers_lexical_overlap() -> None:
    ranked = rerank_candidates(
        query="alpha beta",
        matches=[
            {"path": "one.md", "snippet": "alpha alpha", "distance": 0.4},
            {"path": "two.md", "snippet": "beta", "distance": 0.05},
        ],
        limit=2,
    )

    assert ranked[0]["path"] == "one.md"
    assert ranked[0]["matching_tokens"] == ["alpha"]
    assert ranked[0]["combined_score"] >= ranked[1]["combined_score"]
