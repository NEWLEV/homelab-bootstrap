# Hermes Deployment Plan

Hermes will be added as a second assistant runtime beside OpenClaw.

## Goal

Run Hermes with its own state, config, and lifecycle while reusing approved
infrastructure such as Local RAG, MCP, and selected messaging integrations.

## Deployment steps

1. Install Hermes into a dedicated runtime location.
2. Give Hermes its own `~/.hermes/` state directory.
3. Point Hermes at the existing Local RAG API for grounded retrieval.
4. Register only approved MCP servers.
5. Enable skills and memory under Hermes-specific paths.
6. Add an optional API gateway only after the runtime is healthy.
7. Publish a dashboard shortcut once a stable Hermes URL exists.

## Recommended service shape

- One Hermes service or container.
- Separate from OpenClaw and its secrets.
- Shared infrastructure only through approved network services.

## Suggested first checks

- Hermes starts cleanly.
- Hermes can reach Local RAG.
- Hermes can load MCP servers.
- Hermes memory and skills directories are writable.
- OpenClaw still serves the control UI at `https://aisha.tail4553c9.ts.net/openclaw/`.

## Dashboard note

Until Hermes has a live URL, the Homepage dashboard should show a clear
Hermes blueprint entry instead of a broken shortcut.
