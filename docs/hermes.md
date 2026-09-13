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

The Compose service pins Hermes to the known-good image digest
`nousresearch/hermes-agent@sha256:984813f70658b8ef6d78cb48a56c798c36dc1db20ac7f99cb0b5d55436f1a69b`
by default. Override `HERMES_IMAGE` only after validating the replacement image
on the target architecture.

On container-backed installs, the service seeds the default Hermes gateway with
`HERMES_GATEWAY_BOOTSTRAP_STATE=running`. The installer also repairs only
transient failed startup markers in `/srv/data/services/hermes/gateway_state.json`
(`starting` or `startup_failed`) by backing up the marker and restoring the
operator intent to `running`. Deliberate stopped state is preserved.

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
