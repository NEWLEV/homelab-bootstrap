import hashlib
import os
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
    existing_ids = set(existing.get("ids", []))

    desired_ids: set[str] = set()
    indexed_files = 0
    added_chunks = 0
    skipped_chunks = 0

    for path in sorted(SOURCE_ROOT.rglob("*")):
        if not is_allowed(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        relative = path.relative_to(SOURCE_ROOT).as_posix()
        indexed_files += 1

        new_ids: list[str] = []
        new_documents: list[str] = []
        new_embeddings: list[list[float]] = []
        new_metadatas: list[dict[str, str | int]] = []

        for line_start, line_end, chunk in chunk_text(text):
            digest = chunk_id(relative, line_start, line_end, chunk)
            desired_ids.add(digest)

            if digest in existing_ids:
                skipped_chunks += 1
                continue

            new_ids.append(digest)
            new_documents.append(chunk)
            new_embeddings.append(embed(chunk))
            new_metadatas.append(
                {
                    "path": relative,
                    "line_start": line_start,
                    "line_end": line_end,
                }
            )

        if new_ids:
            collection.upsert(
                ids=new_ids,
                documents=new_documents,
                embeddings=new_embeddings,
                metadatas=new_metadatas,
            )
            added_chunks += len(new_ids)

    stale_ids = sorted(existing_ids - desired_ids)

    if stale_ids:
        collection.delete(ids=stale_ids)

    return {
        "files": indexed_files,
        "added_chunks": added_chunks,
        "skipped_chunks": skipped_chunks,
        "removed_chunks": len(stale_ids),
        "total_chunks": collection.count(),
    }
