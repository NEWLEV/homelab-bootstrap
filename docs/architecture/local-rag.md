# Local RAG Knowledge Base

## Goal

Enable Aisha to answer questions about:

- the homelab-bootstrap repository
- operational documentation
- service configuration
- backup and recovery procedures
- OpenClaw agent workspaces

## Initial Scope

- local-first indexing
- repository and Markdown ingestion
- source citations in answers
- incremental re-indexing
- no secrets indexed
- no automatic write access to source documents

## Proposed Architecture

1. Document collector
2. Text normalization and chunking
3. Local embedding model
4. Vector database
5. Retrieval API
6. OpenClaw integration
7. Scheduled incremental indexing

## Recommended Stack

- Indexer/API: Python FastAPI service
- Embeddings: Ollama with `nomic-embed-text`
- Vector database: Qdrant
- Storage: `/srv/data/services/local-rag`
- Integration: private OpenClaw retrieval tool
- Scheduling: incremental indexing through a systemd timer

## Initial File Types

- Markdown
- YAML
- JSON
- shell scripts
- Docker Compose files
- systemd units
- plain text

## Chunking Strategy

- Prose: 800–1,200 tokens
- Overlap: 100–150 tokens
- Structured files: smaller semantic chunks
- Preserve path, line range, heading, commit SHA, file hash, and chunk hash

## Retrieval Contract

The retrieval service returns evidence. OpenClaw generates the final answer from that evidence.

Each result must include data shaped like:

```json
{
  "path": "scripts/backup",
  "line_start": 32,
  "line_end": 40,
  "commit": "git-commit-sha",
  "heading": null,
  "snippet": "restic backup ..."
}
```

## Security Requirements

- Mount indexed source repositories read-only.
- Do not expose Qdrant publicly.
- Bind the retrieval API to localhost or a private container network.
- Exclude secrets, credentials, private keys, `.env` files, caches, and `.git`.
- Require explicit approval for destructive full re-indexing.
- Keep personal workspace indexing opt-in.

## Backup Strategy

- Back up configuration and Qdrant metadata.
- Treat embeddings and downloaded model caches as rebuildable.
- Exclude large Ollama model caches from Restic.
- Keep source documents as the source of truth.
- Add restore verification after deployment.

## OpenClaw Integration

Expose a private retrieval tool with an interface such as:

```text
local_rag.search(query, filters, limit)
```

Search results must return cited source chunks rather than uncited generated answers.

Workspace filters should support:

- infrastructure
- development
- research
- personal

Personal workspace indexing remains disabled unless explicitly enabled.
