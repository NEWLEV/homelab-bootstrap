import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import chromadb
import httpx

SOURCE_ROOT = Path(
    os.environ.get(
        "SOURCE_ROOT",
        "/sources/homelab-bootstrap",
    )
)
CHROMA_PATH = Path(
    os.environ.get(
        "CHROMA_PATH",
        "/data/chroma",
    )
)
OLLAMA_URL = os.environ.get(
    "OLLAMA_URL",
    "http://ollama:11434",
)
EMBEDDING_PROFILE = os.environ.get(
    "EMBEDDING_PROFILE",
    "balanced",
).strip().lower()
EMBEDDING_PROFILE_MAP = {
    "compact": {
        "model": "all-MiniLM-L6-v2",
        "fallbacks": ["nomic-embed-text"],
    },
    "balanced": {
        "model": "nomic-embed-text",
        "fallbacks": ["all-MiniLM-L6-v2", "bge-small-en-v1.5"],
    },
    "accurate": {
        "model": "bge-small-en-v1.5",
        "fallbacks": ["nomic-embed-text", "all-MiniLM-L6-v2"],
    },
}
EMBEDDING_PROFILE_NAME = EMBEDDING_PROFILE if EMBEDDING_PROFILE in EMBEDDING_PROFILE_MAP else "balanced"
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    EMBEDDING_PROFILE_MAP[EMBEDDING_PROFILE_NAME]["model"],
)
EMBEDDING_MODEL_FALLBACKS = [
    model.strip()
    for model in os.environ.get(
        "EMBEDDING_MODEL_FALLBACKS",
        ",".join(EMBEDDING_PROFILE_MAP[EMBEDDING_PROFILE_NAME]["fallbacks"]),
    ).split(",")
    if model.strip() and model.strip() != EMBEDDING_MODEL
]

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
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "backups",
    "cache",
    "caches",
    "credentials",
    "secrets",
    "site-packages",
    "workspaces",
}

EXCLUDED_FILE_NAMES = {
    "conversation-request.json",
    "grounded-request.json",
    "diagnose-generation.py",
}

EXCLUDED_PATH_FRAGMENTS = (
    "/bootstrap/prep-bundle-",
    "/bootstrap/bundle-test/",
    "/bootstrap/ai-services-bundle-test/",
    "/bootstrap/skills-bundle-test/",
    "/bootstrap/bootstrap.prep-",
    "/bootstrap/compose.prep-",
    "/bootstrap/bootstrap.write-test.json",
    "/bootstrap/compose.write-test.yaml",
)

REQUIRED_METADATA_FIELDS = {
    "path",
    "directory",
    "filename",
    "extension",
    "line_start",
    "line_end",
    "file_hash",
}

MAX_CHARS = 4000
OVERLAP_CHARS = 400


def is_allowed(path: Path) -> bool:
    if not path.is_file():
        return False

    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False

    lowered_parts = {
        part.lower()
        for part in path.parts
    }

    if lowered_parts & EXCLUDED_PARTS:
        return False

    normalized_path = path.as_posix().lower()
    if any(fragment in normalized_path for fragment in EXCLUDED_PATH_FRAGMENTS):
        return False

    name = path.name.lower()

    if name in EXCLUDED_FILE_NAMES:
        return False

    if name.endswith(
        (
            ".key",
            ".crt",
            ".pem",
        )
    ):
        return False

    return True


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for block in iter(
            lambda: source.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def chunk_text(
    text: str,
) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    start = 0

    while start < len(text):
        end = min(
            len(text),
            start + MAX_CHARS,
        )
        chunk = text[start:end].strip()

        if chunk:
            line_start = (
                text.count(
                    "\n",
                    0,
                    start,
                )
                + 1
            )
            line_end = (
                text.count(
                    "\n",
                    0,
                    end,
                )
                + 1
            )

            chunks.append(
                (
                    line_start,
                    line_end,
                    chunk,
                )
            )

        if end >= len(text):
            break

        start = max(
            end - OVERLAP_CHARS,
            start + 1,
        )

    return chunks


def _embedding_models() -> list[str]:
    return [EMBEDDING_MODEL, *EMBEDDING_MODEL_FALLBACKS]


def _embed_once(model: str, text: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": model,
            "input": text,
        },
        timeout=120,
    )
    response.raise_for_status()
    embeddings = response.json().get(
        "embeddings",
        [],
    )
    if not embeddings:
        raise RuntimeError(
            "Ollama returned no embedding.",
        )
    return embeddings[0]


def embed(text: str) -> list[float]:
    last_error: Exception | None = None
    for model in _embedding_models():
        try:
            return _embed_once(model, text)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"All embedding models failed: {last_error}")


def chunk_id(
    relative_path: str,
    line_start: int,
    line_end: int,
    chunk: str,
) -> str:
    value = (
        f"{relative_path}:"
        f"{line_start}:"
        f"{line_end}:"
        f"{chunk}"
    )

    return hashlib.sha256(
        value.encode(),
    ).hexdigest()


def has_required_metadata(
    metadata: dict[str, Any],
) -> bool:
    if not REQUIRED_METADATA_FIELDS.issubset(
        metadata.keys()
    ):
        return False

    string_fields = (
        "path",
        "directory",
        "filename",
        "extension",
        "file_hash",
    )

    if not all(
        isinstance(metadata.get(field), str)
        for field in string_fields
    ):
        return False

    integer_fields = (
        "line_start",
        "line_end",
    )

    return all(
        isinstance(metadata.get(field), int)
        for field in integer_fields
    )


def index_repository() -> dict[str, Any]:
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
    )

    collection = client.get_or_create_collection(
        name="homelab_bootstrap",
        metadata={
            "description": (
                "Aisha homelab repository"
            ),
        },
    )

    existing = collection.get(
        include=[
            "metadatas",
        ]
    )

    existing_ids = existing.get(
        "ids",
        [],
    )
    existing_metadatas = existing.get(
        "metadatas",
        [],
    )

    existing_ids_by_path: dict[
        str,
        set[str],
    ] = defaultdict(set)

    existing_hashes_by_path: dict[
        str,
        set[str],
    ] = defaultdict(set)

    metadata_complete_by_path: dict[
        str,
        bool,
    ] = {}

    for record_id, metadata in zip(
        existing_ids,
        existing_metadatas,
        strict=False,
    ):
        if not metadata:
            continue

        stored_path = metadata.get("path")
        stored_file_hash = metadata.get(
            "file_hash"
        )

        if not isinstance(stored_path, str):
            continue

        existing_ids_by_path[
            stored_path
        ].add(record_id)

        if isinstance(
            stored_file_hash,
            str,
        ):
            existing_hashes_by_path[
                stored_path
            ].add(stored_file_hash)

        record_is_complete = (
            has_required_metadata(metadata)
        )

        metadata_complete_by_path[
            stored_path
        ] = (
            metadata_complete_by_path.get(
                stored_path,
                True,
            )
            and record_is_complete
        )

    existing_id_set = set(existing_ids)
    desired_ids: set[str] = set()

    indexed_files = 0
    skipped_files = 0
    metadata_migrated_files = 0
    added_chunks = 0
    updated_chunks = 0
    skipped_chunks = 0

    for path in sorted(
        SOURCE_ROOT.rglob("*")
    ):
        if not is_allowed(path):
            continue

        relative_path = path.relative_to(
            SOURCE_ROOT
        )
        relative = relative_path.as_posix()

        try:
            current_file_hash = file_hash(path)
        except OSError:
            continue

        stored_hashes = (
            existing_hashes_by_path.get(
                relative,
                set(),
            )
        )
        stored_ids = (
            existing_ids_by_path.get(
                relative,
                set(),
            )
        )
        metadata_is_complete = (
            metadata_complete_by_path.get(
                relative,
                False,
            )
        )

        content_is_unchanged = (
            bool(stored_ids)
            and len(stored_hashes) == 1
            and current_file_hash
            in stored_hashes
        )

        if (
            content_is_unchanged
            and metadata_is_complete
        ):
            desired_ids.update(stored_ids)
            indexed_files += 1
            skipped_files += 1
            skipped_chunks += len(stored_ids)
            continue

        if (
            content_is_unchanged
            and not metadata_is_complete
        ):
            metadata_migrated_files += 1

        try:
            text = path.read_text(
                encoding="utf-8",
            )
        except (
            UnicodeDecodeError,
            OSError,
        ):
            continue

        indexed_files += 1

        new_ids: list[str] = []
        new_documents: list[str] = []
        new_embeddings: list[list[float]] = []
        new_metadatas: list[
            dict[str, str | int]
        ] = []

        directory = (
            relative_path.parent.as_posix()
            if relative_path.parent
            != Path(".")
            else ""
        )
        filename = relative_path.name
        extension = (
            relative_path.suffix.lower()
        )

        for (
            line_start,
            line_end,
            chunk,
        ) in chunk_text(text):
            digest = chunk_id(
                relative,
                line_start,
                line_end,
                chunk,
            )

            desired_ids.add(digest)
            new_ids.append(digest)
            new_documents.append(chunk)
            new_embeddings.append(
                embed(chunk)
            )
            new_metadatas.append(
                {
                    "path": relative,
                    "directory": directory,
                    "filename": filename,
                    "extension": extension,
                    "line_start": line_start,
                    "line_end": line_end,
                    "file_hash": (
                        current_file_hash
                    ),
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

    stale_ids = sorted(
        existing_id_set - desired_ids
    )

    if stale_ids:
        collection.delete(
            ids=stale_ids,
        )

    return {
        "files": indexed_files,
        "skipped_files": skipped_files,
        "metadata_migrated_files": (
            metadata_migrated_files
        ),
        "added_chunks": added_chunks,
        "updated_chunks": updated_chunks,
        "skipped_chunks": skipped_chunks,
        "removed_chunks": len(stale_ids),
        "total_chunks": collection.count(),
    }


def build_index_status(collection: Any) -> dict[str, Any]:
    return {
        "collection": collection.name,
        "chunks": collection.count(),
        "incremental_updates": True,
        "metadata_migration_supported": True,
        "content_hashing": True,
        "stale_chunk_cleanup": True,
        "embedding_profile": EMBEDDING_PROFILE_NAME,
        "required_metadata_fields": sorted(REQUIRED_METADATA_FIELDS),
    }
