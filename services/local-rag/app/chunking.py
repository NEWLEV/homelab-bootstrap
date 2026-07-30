import re
from pathlib import Path


MAX_CHARS = 4000
OVERLAP_CHARS = 400

MARKDOWN_BOUNDARY = re.compile(r"^#{1,6}\s+\S")
YAML_BOUNDARY = re.compile(
    r"^(?:[A-Za-z0-9_.-]+| {2}[A-Za-z0-9_.-]+):(?:\s|$)"
)
SHELL_BOUNDARY = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{\s*$"
)
SYSTEMD_BOUNDARY = re.compile(r"^\[[A-Za-z0-9_.@-]+\]\s*$")
JSON_BOUNDARY = re.compile(r'^  "[^"\\]+"\s*:\s*')
PYTHON_BOUNDARY = re.compile(
    r"^(?:async\s+def|def|class)\s+[A-Za-z_][A-Za-z0-9_]*"
)


def chunk_text(
    text: str,
    *,
    max_chars: int = MAX_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
    line_offset: int = 0,
) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end].strip()

        if chunk:
            line_start = line_offset + text.count("\n", 0, start) + 1
            line_end = line_offset + text.count("\n", 0, end) + 1
            chunks.append((line_start, line_end, chunk))

        if end >= len(text):
            break

        start = max(end - overlap_chars, start + 1)

    return chunks


def boundary_pattern(path: Path, text: str) -> re.Pattern[str] | None:
    suffix = path.suffix.lower()

    if suffix == ".md":
        return MARKDOWN_BOUNDARY
    if suffix in {".yml", ".yaml"}:
        return YAML_BOUNDARY
    if suffix in {".service", ".timer"}:
        return SYSTEMD_BOUNDARY
    if suffix == ".json":
        return JSON_BOUNDARY
    if suffix == ".py":
        return PYTHON_BOUNDARY
    if suffix == ".sh" or text.startswith("#!/usr/bin/env bash"):
        return SHELL_BOUNDARY

    return None


def structural_boundaries(path: Path, text: str) -> list[int]:
    lines = text.splitlines(keepends=True)
    pattern = boundary_pattern(path, text)

    if not lines or pattern is None:
        return [0]

    boundaries = {0}
    for index, line in enumerate(lines):
        if pattern.match(line.rstrip("\r\n")):
            boundaries.add(index)

    return sorted(boundaries)


def line_offsets(lines: list[str]) -> list[int]:
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    return offsets


def structural_spans(path: Path, text: str) -> list[tuple[int, int, int]]:
    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    offsets = line_offsets(lines)
    boundaries = structural_boundaries(path, text)
    spans: list[tuple[int, int, int]] = []

    for position, start_line in enumerate(boundaries):
        end_line = (
            boundaries[position + 1]
            if position + 1 < len(boundaries)
            else len(lines)
        )
        spans.append((offsets[start_line], offsets[end_line], start_line))

    return spans


def pack_spans(
    text: str,
    spans: list[tuple[int, int, int]],
    max_chars: int,
) -> list[tuple[int, int, int]]:
    if not spans:
        return []

    packed: list[tuple[int, int, int]] = []
    current_start, current_end, current_line = spans[0]

    for start, end, start_line in spans[1:]:
        if end - current_start <= max_chars:
            current_end = end
            continue

        packed.append((current_start, current_end, current_line))
        current_start = start
        current_end = end
        current_line = start_line

    packed.append((current_start, current_end, current_line))
    return packed


def chunk_document(
    path: Path,
    text: str,
    *,
    max_chars: int = MAX_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[tuple[int, int, str]]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between 0 and max_chars")

    spans = structural_spans(path, text)
    if not spans:
        return []

    chunks: list[tuple[int, int, str]] = []
    for start, end, start_line in pack_spans(text, spans, max_chars):
        section = text[start:end]
        if len(section) > max_chars:
            chunks.extend(
                chunk_text(
                    section,
                    max_chars=max_chars,
                    overlap_chars=overlap_chars,
                    line_offset=start_line,
                )
            )
            continue

        chunk = section.strip()
        if not chunk:
            continue
        line_start = start_line + 1
        line_end = start_line + section.count("\n") + 1
        chunks.append((line_start, line_end, chunk))

    return chunks
