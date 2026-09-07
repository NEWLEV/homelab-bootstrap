# Hermes Runtime

Hermes is a second assistant runtime that lives beside OpenClaw without
replacing it.

## Purpose

```text
~/.hermes/
  config.yaml
  .env
  memories/
  sessions/
  logs/
  skills/
  cron/
```

Hermes keeps its own state, skills, sessions, and MCP config under
`~/.hermes/` while reusing approved infrastructure such as Local RAG.

Hermes state lives under `/srv/data/services/hermes/`, so it follows the
normal service-data backup and restore flow used by the rest of Aisha.

## Access and boundaries

- OpenClaw is mounted read-only at `/workspace/openclaw`.
- Hermes can inspect the OpenClaw checkout when the compose service includes
  the repo bind mount.
- Hermes reuses Local RAG instead of duplicating the index.
- Hermes can use skills and approved MCP servers without sharing OpenClaw
  secrets or state.
- Hermes should keep separate state and policy files from OpenClaw.
- Enable Slack or Discord only after the same tailnet and secrets boundary is
  validated.

## Minimum verification checklist

1. Hermes starts with its own config and state directory.
2. Hermes can reach Local RAG over the private Docker network.
3. Hermes can load approved MCP servers.
4. Hermes memory and skills paths are writable.
5. Hermes can inspect the OpenClaw repo at `/workspace/openclaw`.
6. Hermes dashboard responds at `http://aisha:9119/`.
7. The native OpenClaw Control UI is available at
   `https://aisha.tail4553c9.ts.net/openclaw/`; the Aisha chat gateway is
   available separately at `https://aisha.tail4553c9.ts.net/aisha/`.
