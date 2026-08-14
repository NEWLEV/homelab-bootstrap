# Hermes Service Blueprint

Hermes is the second assistant runtime planned for this appliance. It is
kept separate from OpenClaw so each runtime has its own config, memory,
skills, and lifecycle.

## Responsibilities

- Run Hermes as an isolated assistant runtime.
- Reuse Local RAG, MCP, and approved infrastructure services.
- Keep Hermes state under `~/.hermes/` or a dedicated host volume.
- Avoid sharing OpenClaw secrets or browser-facing code paths.

## Recommended runtime boundaries

- Hermes gateway/API: separate service or container.
- Hermes state: `~/.hermes/`.
- Hermes config: `~/.hermes/config.yaml`.
- Hermes environment: `~/.hermes/.env`.

## Suggested dependencies

- Local RAG for grounded retrieval.
- Selected MCP servers from the approved inventory.
- Optional messaging integrations after the gateway is confirmed.

## Verification

- Hermes starts cleanly.
- Hermes can reach Local RAG.
- Hermes can load approved skills and MCP servers.
- OpenClaw still remains available at its own routes.

This directory intentionally stays minimal until a live Hermes deployment is
approved.
