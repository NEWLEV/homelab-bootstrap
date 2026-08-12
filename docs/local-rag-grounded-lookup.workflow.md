# `local-rag-grounded-lookup` workflow export

This file is a checked-in backup of the live n8n workflow used for the local RAG grounded lookup example.

## Files

- [Workflow JSON](./local-rag-grounded-lookup.workflow.json)

## Restore

Import `local-rag-grounded-lookup.workflow.json` into n8n if the live workflow needs to be recreated.
After import, verify:

- `Manual Trigger`
- `Set Lookup Question`
- `Query Local RAG`
- `Finalize Answer`

are wired in that order.
