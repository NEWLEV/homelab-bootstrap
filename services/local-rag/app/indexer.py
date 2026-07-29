import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import chromadb
import httpx

SOURCE_ROOT = Path(os.environ.get("SOURCE_ROOT", "/sources/homelab-bootstrap"))
CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "/data/chroma"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")

ALLOWED_SUFFIXES = {
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".sh",
    ".service",
    ".timer",
}

EXCLUDED_PARTS = {
    ".git",
    ".env",
    "__pycache__",
    "node_modules",
    "backups",
    "cache",
    "caches",
    "credentials",
    "secrets",
    "workspaces",
}

MAX_CHARS = 4000
OVERLAP_CHARS = 400


def is_allowed(path: Path) -> bool:
    if not path.is_file():
        return False

    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False

    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & EXCLUDED_PARTS:
        return False

    name = path.name.lower()
    if name.endswith((".key", ".crt", ".pem")):
        return False

    return True


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def chunk_text(text: str) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    start = 0

    while start < len(text):
        end = min(len(text), start + MAX_CHARS)
        chunk = text[start:end].strip()

        if chunk:
            line_start = text.count("\n", 0, start) + 1
            line_end = text.count("\n", 0, end) + 1
            chunks.append((line_start, line_end, chunk))

        if end >= len(text):
            break

        start = max(end - OVERLAP_CHARS, start + 1)

    return chunks


def embed(text: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
        },
        timeout=120,
    )
    response.raise_for_status()

    embeddings = response.json().get("embeddings", [])
    if not embeddings:
        raise RuntimeError("Ollama returned no embedding.")

    return embeddings[0]


def chunk_id(
    relative_path: str,
    line_start: int,
    line_end: int,
    chunk: str,
) -> str:
    value = f"{relative_path}:{line_start}:{line_end}:{chunk}"
    return hashlib.sha256(value.encode()).hexdigest()


def index_repository() -> dict[str, Any]:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name="homelab_bootstrap",
        metadata={"description": "Aisha homelab repository"},
    )

    existing = collection.get(include=["metadatas"])
    existing_ids = existing.get("ids", [])
    existing_metadatas = existing.get("metadatas", [])

    existing_ids_by_path: dict[str, set[str]] = defaultdict(set)
    existing_hashes_by_path: dict[str, set[str]] = defaultdict(set)

    for record_id, metadata in zip(
        existing_ids,
        existing_metadatas,
        strict=False,
    ):
        if not metadata:
            continue

        path = metadata.get("path")
        stored_file_hash = metadata.get("file_hash")

        if isinstance(path, str):
            existing_ids_by_path[path].add(record_id)

            if isinstance(stored_file_hash, str):
                existing_hashes_by_path[path].add(stored_file_hash)

    existing_id_set = set(existing_ids)
    desired_ids: set[str] = set()

    indexed_files = 0
    skipped_files = 0
    added_chunks = 0
    updated_chunks = 0
    skipped_chunks = 0

    for path in sorted(SOURCE_ROOT.rglob("*")):
        if not is_allowed(path):
            continue

        relative = path.relative_to(SOURCE_ROOT).as_posix()

        try:
            current_file_hash = file_hash(path)
        except OSError:
            continue

        stored_hashes = existing_hashes_by_path.get(relative, set())
        stored_ids = existing_ids_by_path.get(relative, set())

        if (
            stored_ids
            and len(stored_hashes) == 1
            and current_file_hash in stored_hashes
        ):
            desired_ids.update(stored_ids)
            indexed_files += 1
            skipped_files += 1
            skipped_chunks += len(stored_ids)
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        indexed_files += 1

        new_ids: list[str] = []
        new_documents: list[str] = []
        new_embeddings: list[list[float]] = []
        new_metadatas: list[dict[str, str | int]] = []

        for line_start, line_end, chunk in chunk_text(text):
            digest = chunk_id(relative, line_start, line_end, chunk)
            desired_ids.add(digest)

            new_ids.append(digest)
            new_documents.append(chunk)
            new_embeddings.append(embed(chunk))
            new_metadatas.append(
                {
                    "path": relative,
                    "line_start": line_start,
                    "line_end": line_end,
                    "file_hash": current_file_hash,
                }
            )

            if digest in existing_id_set:
                updated_chunks += 1
            else:
                added_chunks += 1

        if new_ids:
            collection.upsert(
                ids=new_ids,
                documents=new_documents,
                embeddings=new_embeddings,
                metadatas=new_metadatas,
            )

    stale_ids = sorted(existing_id_set - desired_ids)

    if stale_ids:
        collection.delete(ids=stale_ids)

    return {
        "files": indexed_files,
        "skipped_files": skipped_files,
        "added_chunks": added_chunks,
        "updated_chunks": updated_chunks,
        "skipped_chunks": skipped_chunks,
        "removed_chunks": len(stale_ids),
        "total_chunks": collection.count(),
    }
