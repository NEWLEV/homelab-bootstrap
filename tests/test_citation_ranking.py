import os
from pathlib import Path

os.environ["CHROMA_PATH"] = str(Path("C:/Users/ZBook/Documents/Aisha/.test-chroma"))

from app.main import extract_used_citations


def test_extract_used_citations_ranks_overlap() -> None:
    citations = extract_used_citations(
        "Answer mentions alpha [2] and beta [1].",
        [
            {"path": "one.md", "line_start": 1, "line_end": 2, "distance": 0.4, "snippet": "beta beta"},
            {"path": "two.md", "line_start": 3, "line_end": 4, "distance": 0.1, "snippet": "alpha beta gamma"},
        ],
    )

    assert [citation.path for citation in citations] == ["two.md", "one.md"]


def test_build_grounded_prompt_groups_chunks_by_source() -> None:
    from app.main import build_grounded_prompt

    prompt = build_grounded_prompt(
        "What changed?",
        [
            {"path": "one.md", "line_start": 1, "line_end": 2, "distance": 0.4, "snippet": "alpha"},
            {"path": "one.md", "line_start": 3, "line_end": 4, "distance": 0.2, "snippet": "beta"},
            {"path": "two.md", "line_start": 1, "line_end": 1, "distance": 0.1, "snippet": "gamma"},
        ],
    )

    assert "Source 1: one.md" in prompt
    assert "[1.1] 1-2 alpha" in prompt
    assert "[1.2] 3-4 beta" in prompt
    assert "Source 2: two.md" in prompt
