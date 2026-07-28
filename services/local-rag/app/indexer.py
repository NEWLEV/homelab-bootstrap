import hashlib
import os
from pathlib import Path

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


def index_repository() -> dict[str, int]:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        name="homelab_bootstrap",
        metadata={"description": "Aisha homelab repository"},
    )

    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, str | int]] = []
    ids: list[str] = []

    indexed_files = 0

    for path in sorted(SOURCE_ROOT.rglob("*")):
        if not is_allowed(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        relative = path.relative_to(SOURCE_ROOT).as_posix()
        file_chunks = chunk_text(text)

        for line_start, line_end, chunk in file_chunks:
            digest = hashlib.sha256(
                f"{relative}:{line_start}:{line_end}:{chunk}".encode()
            ).hexdigest()

            ids.append(digest)
            documents.append(chunk)
            embeddings.append(embed(chunk))
            metadatas.append(
                {
                    "path": relative,
                    "line_start": line_start,
                    "line_end": line_end,
                }
            )

        indexed_files += 1

    if ids:
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    return {
        "files": indexed_files,
        "chunks": len(ids),
    }
