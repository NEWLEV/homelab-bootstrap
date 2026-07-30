from pathlib import Path
from typing import Any

import app.indexer as indexer


class FakeCollection:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    def get(self, include: list[str] | None = None) -> dict[str, Any]:
        return {
            "ids": list(self.records),
            "metadatas": [
                record["metadata"] for record in self.records.values()
            ],
        }

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, str | int]],
    ) -> None:
        for record_id, document, embedding, metadata in zip(
            ids,
            documents,
            embeddings,
            metadatas,
            strict=True,
        ):
            self.records[record_id] = {
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
            }

    def delete(self, ids: list[str]) -> None:
        for record_id in ids:
            self.records.pop(record_id, None)

    def count(self) -> int:
        return len(self.records)


class FakeClient:
    def __init__(self, collection: FakeCollection) -> None:
        self.collection = collection

    def get_or_create_collection(
        self,
        name: str,
        metadata: dict[str, str],
    ) -> FakeCollection:
        assert name == "homelab_bootstrap"
        assert metadata["description"] == "Aisha homelab repository"
        return self.collection


def configure_indexer(
    monkeypatch,
    source_root: Path,
    collection: FakeCollection,
) -> None:
    monkeypatch.setattr(indexer, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(
        indexer.chromadb,
        "PersistentClient",
        lambda path: FakeClient(collection),
    )
    monkeypatch.setattr(
        indexer,
        "embed",
        lambda text: [float(len(text))],
    )


def test_chunk_id_is_stable() -> None:
    first = indexer.chunk_id("README.md", 1, 3, "hello")
    second = indexer.chunk_id("README.md", 1, 3, "hello")

    assert first == second
    assert len(first) == 64


def test_chunk_id_changes_when_content_changes() -> None:
    original = indexer.chunk_id("README.md", 1, 3, "hello")
    modified = indexer.chunk_id("README.md", 1, 3, "updated")

    assert original != modified


def test_repeated_indexing_skips_existing_chunks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()

    (source_root / "README.md").write_text(
        "Aisha homelab documentation",
        encoding="utf-8",
    )

    collection = FakeCollection()
    embed_calls: list[str] = []

    monkeypatch.setattr(indexer, "SOURCE_ROOT", source_root)
    monkeypatch.setattr(
        indexer.chromadb,
        "PersistentClient",
        lambda path: FakeClient(collection),
    )
    monkeypatch.setattr(
        indexer,
        "embed",
        lambda text: embed_calls.append(text) or [float(len(text))],
    )

    first = indexer.index_repository()
    second = indexer.index_repository()

    assert len(embed_calls) == 1

    assert first == {
        "files": 1,
        "skipped_files": 0,
        "added_chunks": 1,
        "updated_chunks": 0,
        "skipped_chunks": 0,
        "removed_chunks": 0,
        "metadata_migrated_files": 0,
        "total_chunks": 1,
    }

    assert second == {
        "files": 1,
        "skipped_files": 1,
        "added_chunks": 0,
        "updated_chunks": 0,
        "skipped_chunks": 1,
        "removed_chunks": 0,
        "metadata_migrated_files": 0,
        "total_chunks": 1,
    }


def test_modified_file_replaces_stale_chunks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()

    document = source_root / "README.md"
    document.write_text(
        "Original documentation",
        encoding="utf-8",
    )

    collection = FakeCollection()
    configure_indexer(monkeypatch, source_root, collection)

    first = indexer.index_repository()
    original_ids = set(collection.records)

    document.write_text(
        "Updated documentation",
        encoding="utf-8",
    )

    second = indexer.index_repository()
    updated_ids = set(collection.records)

    assert first["added_chunks"] == 1
    assert first["updated_chunks"] == 0
    assert second["added_chunks"] == 1
    assert second["updated_chunks"] == 0
    assert second["removed_chunks"] == 1
    assert second["total_chunks"] == 1
    assert original_ids != updated_ids


def test_deleted_file_removes_stale_chunks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()

    document = source_root / "README.md"
    document.write_text(
        "Temporary documentation",
        encoding="utf-8",
    )

    collection = FakeCollection()
    configure_indexer(monkeypatch, source_root, collection)

    indexer.index_repository()
    assert collection.count() == 1

    document.unlink()
    result = indexer.index_repository()

    assert result == {
        "files": 0,
        "skipped_files": 0,
        "added_chunks": 0,
        "updated_chunks": 0,
        "skipped_chunks": 0,
        "removed_chunks": 1,
        "metadata_migrated_files": 0,
        "total_chunks": 0,
    }


def test_excluded_paths_are_not_indexed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()

    (source_root / "README.md").write_text(
        "Allowed",
        encoding="utf-8",
    )

    secrets = source_root / "secrets"
    secrets.mkdir()
    (secrets / "passwords.txt").write_text(
        "Should not be indexed",
        encoding="utf-8",
    )

    git_directory = source_root / ".git"
    git_directory.mkdir()
    (git_directory / "config").write_text(
        "Should not be indexed",
        encoding="utf-8",
    )

    collection = FakeCollection()
    configure_indexer(monkeypatch, source_root, collection)

    result = indexer.index_repository()

    assert result["files"] == 1
    assert result["total_chunks"] == 1

    stored_paths = {
        record["metadata"]["path"]
        for record in collection.records.values()
    }

    assert stored_paths == {"README.md"}


def test_local_rag_evaluation_fixtures_are_removed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()

    (source_root / "README.md").write_text(
        "Allowed production documentation",
        encoding="utf-8",
    )
    evaluation = source_root / "services" / "local-rag" / "evaluation"
    evaluation.mkdir(parents=True)
    (evaluation / "cases.json").write_text(
        '{"query": "local-rag.yml"}',
        encoding="utf-8",
    )

    collection = FakeCollection()
    configure_indexer(monkeypatch, source_root, collection)
    excluded_prefixes = indexer.EXCLUDED_RELATIVE_PREFIXES

    monkeypatch.setattr(indexer, "EXCLUDED_RELATIVE_PREFIXES", set())
    first = indexer.index_repository()
    assert first["total_chunks"] == 2

    monkeypatch.setattr(
        indexer,
        "EXCLUDED_RELATIVE_PREFIXES",
        excluded_prefixes,
    )
    second = indexer.index_repository()

    assert second["removed_chunks"] == 1
    assert second["total_chunks"] == 1
    stored_paths = {
        record["metadata"]["path"]
        for record in collection.records.values()
    }
    assert stored_paths == {"README.md"}


def test_chunking_version_change_reindexes_unchanged_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "repository"
    source_root.mkdir()
    (source_root / "README.md").write_text(
        "Documentation",
        encoding="utf-8",
    )

    collection = FakeCollection()
    configure_indexer(monkeypatch, source_root, collection)
    first = indexer.index_repository()
    assert first["total_chunks"] == 1

    for record in collection.records.values():
        record["metadata"]["chunking_version"] = "1"

    second = indexer.index_repository()

    assert second["metadata_migrated_files"] == 1
    assert second["updated_chunks"] == 1
    assert second["total_chunks"] == 1
    assert all(
        record["metadata"]["chunking_version"]
        == indexer.CHUNKING_VERSION
        for record in collection.records.values()
    )
