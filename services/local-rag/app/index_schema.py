from typing import Any


INDEX_SCHEMA_VERSION = "1"
COLLECTION_DESCRIPTION = "Aisha homelab repository"

REQUIRED_METADATA_FIELDS = {
    "path",
    "directory",
    "filename",
    "extension",
    "line_start",
    "line_end",
    "file_hash",
    "chunking_version",
    "schema_version",
    "embedding_model",
}

STRING_METADATA_FIELDS = {
    "path",
    "directory",
    "filename",
    "extension",
    "file_hash",
    "chunking_version",
    "schema_version",
    "embedding_model",
}
INTEGER_METADATA_FIELDS = {
    "line_start",
    "line_end",
}


def collection_metadata(embedding_model: str) -> dict[str, str]:
    return {
        "description": COLLECTION_DESCRIPTION,
        "schema_version": INDEX_SCHEMA_VERSION,
        "embedding_model": embedding_model,
    }


def metadata_issues(
    metadata: dict[str, Any] | None,
    *,
    chunking_version: str,
    embedding_model: str,
) -> set[str]:
    if not metadata:
        return {"missing_metadata"}

    issues: set[str] = set()
    if not REQUIRED_METADATA_FIELDS.issubset(metadata):
        issues.add("missing_fields")
    if any(
        field in metadata
        and not isinstance(metadata[field], str)
        for field in STRING_METADATA_FIELDS
    ):
        issues.add("invalid_types")
    if any(
        field in metadata
        and not isinstance(metadata[field], int)
        for field in INTEGER_METADATA_FIELDS
    ):
        issues.add("invalid_types")
    if metadata.get("schema_version") != INDEX_SCHEMA_VERSION:
        issues.add("schema_mismatch")
    if metadata.get("chunking_version") != chunking_version:
        issues.add("chunking_mismatch")
    if metadata.get("embedding_model") != embedding_model:
        issues.add("embedding_model_mismatch")
    return issues


def metadata_is_current(
    metadata: dict[str, Any] | None,
    *,
    chunking_version: str,
    embedding_model: str,
) -> bool:
    return not metadata_issues(
        metadata,
        chunking_version=chunking_version,
        embedding_model=embedding_model,
    )


def inspect_collection(
    collection: Any,
    *,
    chunking_version: str,
    embedding_model: str,
) -> dict[str, Any]:
    records = collection.get(include=["metadatas"])
    metadatas = records.get("metadatas", [])
    issue_counts = {
        "missing_metadata_records": 0,
        "missing_field_records": 0,
        "invalid_type_records": 0,
        "schema_mismatch_records": 0,
        "chunking_mismatch_records": 0,
        "embedding_model_mismatch_records": 0,
    }
    invalid_records = 0
    issue_mapping = {
        "missing_metadata": "missing_metadata_records",
        "missing_fields": "missing_field_records",
        "invalid_types": "invalid_type_records",
        "schema_mismatch": "schema_mismatch_records",
        "chunking_mismatch": "chunking_mismatch_records",
        "embedding_model_mismatch": "embedding_model_mismatch_records",
    }

    for metadata in metadatas:
        issues = metadata_issues(
            metadata,
            chunking_version=chunking_version,
            embedding_model=embedding_model,
        )
        if issues:
            invalid_records += 1
        for issue in issues:
            issue_counts[issue_mapping[issue]] += 1

    stored = collection.metadata or {}
    stored_schema = stored.get("schema_version")
    stored_model = stored.get("embedding_model")
    marker_current = (
        stored_schema == INDEX_SCHEMA_VERSION
        and stored_model == embedding_model
    )

    return {
        "valid": invalid_records == 0 and marker_current,
        "reindex_required": invalid_records > 0 or not marker_current,
        "records": len(records.get("ids", [])),
        "invalid_records": invalid_records,
        **issue_counts,
        "schema_version": INDEX_SCHEMA_VERSION,
        "collection_schema_version": stored_schema,
        "embedding_model": embedding_model,
        "collection_embedding_model": stored_model,
        "chunking_version": chunking_version,
    }
