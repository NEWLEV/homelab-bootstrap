# Hermes Service

Hermes is the second assistant runtime for this appliance.

## Responsibilities

- Run Hermes as an isolated assistant runtime with its own state.
- Reuse Local RAG, MCP, and approved infrastructure services.
- Keep Hermes state under `~/.hermes/` or `/srv/data/services/hermes/`.
- Avoid sharing OpenClaw secrets or browser-facing code paths.

## Recommended runtime boundaries

- Hermes gateway/API: separate service or container.
- Hermes state: `~/.hermes/`.
- Hermes config: `~/.hermes/config.yaml`.
- Hermes environment: `~/.hermes/.env`.
- Hermes host runtime: `/srv/data/services/hermes/`.
- OpenClaw checkout mount: `/workspace/openclaw` inside the Hermes container.

## Suggested dependencies

- Local RAG for grounded retrieval.
- Selected MCP servers from the approved inventory.
- Optional messaging integrations after the gateway is confirmed.
- Hermes dashboard at `http://aisha:9119/`.

## Verification

- Hermes starts cleanly.
- Hermes can reach Local RAG.
- Hermes can load approved skills and MCP servers.
- Hermes can read the OpenClaw checkout from `/workspace/openclaw`.
- Hermes state is kept in `/srv/data/services/hermes/`, so the normal service-data backup and restore flow applies.
- OpenClaw still remains available at its own routes.

Use `bash scripts/install-hermes-service.sh` to create the host runtime,
generate the local secrets file, and start the container.
