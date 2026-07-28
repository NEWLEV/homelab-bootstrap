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

## Security Requirements

- exclude secret files, credentials and private keys
- read-only access to indexed sources
- bind APIs to localhost or private Docker networks
- back up metadata and configuration
- require explicit approval for destructive re-indexing

## Decisions Required

- embedding runtime
- vector database
- supported file types
- chunk size and overlap
- OpenClaw integration method
- backup and retention strategy
