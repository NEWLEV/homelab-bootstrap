# ADR 0004: Vector Store

- Status: Accepted
- Date: 2026-08-01

## Context

Local RAG already uses persistent ChromaDB storage. Future long-term memory should reuse existing infrastructure whenever practical.

## Decision

- ChromaDB remains the project's vector store.
- Persistent memory will first be implemented on ChromaDB.
- Qdrant will only be introduced if a documented technical requirement cannot be satisfied by ChromaDB.
- Memory implementation must define schema, retention, backup, restore, and evaluation before deployment.

## Consequences

- A second vector database is avoided unless justified.
- Operational complexity remains lower.
- Existing backup and restore procedures continue to apply.

## Validation

- New memory features are evaluated against ChromaDB first.
- Any proposal to introduce Qdrant documents why ChromaDB is insufficient.
