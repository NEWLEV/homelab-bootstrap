from pathlib import Path

import pytest

from app.chunking import chunk_document


@pytest.mark.parametrize(
    ("path", "text", "expected_starts"),
    [
        (
            Path("docs/recovery.md"),
            "# Recovery\n" + "a" * 50 + "\n## Restore\n" + "b" * 50,
            ["# Recovery", "## Restore"],
        ),
        (
            Path("compose/ai/local-rag.yml"),
            "services:\n  ollama:\n" + "a" * 50 + "\n  api:\n" + "b" * 50,
            ["services:", "api:"],
        ),
        (
            Path("scripts/backup"),
            "#!/usr/bin/env bash\n" + "a" * 50 + "\nrestore() {\n" + "b" * 50,
            ["#!/usr/bin/env bash", "restore() {"],
        ),
        (
            Path("configs/systemd/aisha.service"),
            "[Unit]\n" + "a" * 50 + "\n[Service]\n" + "b" * 50,
            ["[Unit]", "[Service]"],
        ),
        (
            Path("config.json"),
            "{\n  \"agents\": {\n" + "a" * 50 + "\n  \"tools\": {\n" + "b" * 50,
            ["{", "\"tools\": {"],
        ),
        (
            Path("app/main.py"),
            "import os\n" + "a" * 50 + "\ndef health():\n" + "b" * 50,
            ["import os", "def health():"],
        ),
    ],
)
def test_structure_boundaries_are_preserved(
    path: Path,
    text: str,
    expected_starts: list[str],
) -> None:
    chunks = chunk_document(
        path,
        text,
        max_chars=80,
        overlap_chars=10,
    )

    assert len(chunks) == 2
    assert [chunk[2].lstrip().splitlines()[0] for chunk in chunks] == (
        expected_starts
    )


def test_small_adjacent_sections_are_packed() -> None:
    text = "# One\na\n## Two\nb\n"

    chunks = chunk_document(
        Path("README.md"),
        text,
        max_chars=100,
        overlap_chars=10,
    )

    assert chunks == [(1, 5, text.strip())]


def test_oversized_section_uses_overlapping_fallback() -> None:
    text = "# Large\n" + "x" * 120

    chunks = chunk_document(
        Path("README.md"),
        text,
        max_chars=60,
        overlap_chars=10,
    )

    assert len(chunks) == 3
    assert all(len(chunk[2]) <= 60 for chunk in chunks)
    assert chunks[0][2].startswith("# Large")
    assert chunks[0][2][-10:] == chunks[1][2][:10]


def test_line_ranges_follow_structural_sections() -> None:
    text = "# One\nalpha\n## Two\nbeta\n"

    chunks = chunk_document(
        Path("README.md"),
        text,
        max_chars=15,
        overlap_chars=2,
    )

    assert chunks == [
        (1, 3, "# One\nalpha"),
        (3, 5, "## Two\nbeta"),
    ]


def test_unknown_format_preserves_character_chunking() -> None:
    text = "a" * 70

    chunks = chunk_document(
        Path("notes.txt"),
        text,
        max_chars=40,
        overlap_chars=10,
    )

    assert [len(chunk[2]) for chunk in chunks] == [40, 40]


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    [(0, 0), (10, -1), (10, 10)],
)
def test_invalid_chunk_limits_are_rejected(
    max_chars: int,
    overlap_chars: int,
) -> None:
    with pytest.raises(ValueError):
        chunk_document(
            Path("README.md"),
            "content",
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )
