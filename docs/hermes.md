# Hermes Runtime

Hermes is a second assistant runtime that lives beside OpenClaw without
replacing it.

## What Hermes is for

- Separate assistant runtime for experiments, alternate workflows, and
  parallel capability growth.
- Independent memory, skills, sessions, and MCP configuration under
  `~/.hermes/`.
- Optional API gateway and dashboard for external integrations and portal-style
  access.

## Why keep Hermes separate from OpenClaw

- OpenClaw remains the hosted Aisha runtime and dashboard-facing assistant.
- Hermes can be tested, tuned, or replaced without disturbing the current
  OpenClaw control UI or chat gateway.
- The two runtimes can share infrastructure services such as Local RAG and
  approved MCP servers while keeping separate state and policy files.

## Recommended layout

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

## Suggested integration points

- **MCP**: register only approved servers in `~/.hermes/config.yaml`.
- **Local RAG**: point Hermes at the existing Local RAG API rather than
  duplicating an index.
- **Skills**: keep Hermes skills in `~/.hermes/skills/` so they do not drift
  from OpenClaw prompts or the dashboard launcher.
- **Messaging**: enable Slack or Discord only after the gateway is validated
  against the same tailnet and secrets boundary used by the other services.

## Default operating posture

- Use a separate service or container for Hermes.
- Keep secrets out of browser-delivered code.
- Keep OpenClaw and Hermes on distinct state directories and configs.
- Reuse the existing local infrastructure instead of creating a second copy
  of Local RAG or the dashboard stack.

## Minimum verification checklist

1. Hermes starts with its own config and state directory.
2. Hermes can reach Local RAG over the private Docker network.
3. Hermes can load approved MCP servers.
4. Hermes memory and skills paths are writable.
5. Hermes dashboard responds at `http://aisha:9119/`.
6. OpenClaw still serves the control UI at
   `https://aisha.tail4553c9.ts.net/openclaw/`.

## Notes

This repository now treats Hermes as a live second runtime, not as an
implicit replacement for OpenClaw.
