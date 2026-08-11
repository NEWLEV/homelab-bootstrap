# OpenClaw operations

## Operating model

OpenClaw owns interactive agent work, skills, tool calls, and Discord. n8n owns
durable, retryable external workflows. Mission Control is the approval and audit
boundary; it never grants an external workflow permission to execute a risky
action on its own.

Current production profile:

- tool profile: `coding`, with explicit messaging access
- enabled providers: OpenAI, Ollama, and Groq
- enabled plugins: Codex, Discord, and memory-core
- default agent concurrency: four top-level agents and eight subagents
- secure Control UI: `https://aisha.tail4553c9.ts.net/openclaw/`

## Agent coordination

Use a top-level agent for a bounded outcome and subagents only for independent
workstreams. Agents must return evidence and proposed actions to their parent;
only the owner-facing workflow may request approval or trigger an external side
effect. Keep workspaces separated by role and use Mission Control events for
cross-agent handoffs.

## Automation and channels

Install the n8n runtime and dispatcher:

```bash
./scripts/install-n8n-integration
docker compose -f compose/automation/n8n.yml up -d
./scripts/install-tailnet-router
sudo tailscale serve reset
sudo tailscale serve --https=443 http://127.0.0.1:18080
./homelab-bootstrap/services/integrations/scripts/install-integration-dispatcher.sh
```

Import the required workflow export into n8n and activate it before adding its
local webhook endpoint to `~/.config/aisha/integration-dispatcher.env`. Start
the dispatcher timer only after that step. This prevents alerts from being sent
to an unconfigured or unintended endpoint.

## Network healthchecks

The Traefik and socket-proxy Compose file is maintained by the host-level
checkout at `/srv/data/git/homelab-bootstrap`. Apply the repository-managed
healthcheck override without replacing that host configuration:

```bash
docker compose \
  -f /srv/data/git/homelab-bootstrap/compose/networking/traefik.yml \
  -f /srv/data/git/homelab-bootstrap/workspaces/development/repo/compose/networking/traefik-health.yml \
  up -d --force-recreate socket-proxy traefik
```

The override enables Traefik's internal ping handler and checks the Docker
socket proxy's read-only `/_ping` endpoint. It does not publish an additional
host port.
## Local RAG workflow

The `local-rag-grounded-lookup` export gives n8n a manual, read-only lookup
workflow. It is intentionally not scheduled and sends no notifications.

1. Import `scripts/local_rag_grounded_lookup_n8n_export.json` in n8n.
2. Create an HTTP Header Auth credential named `Local RAG API`.
3. Set its header name to `Authorization` and its value to `Bearer <token>`;
   obtain the token locally from the protected Local RAG token file, never from
   a chat prompt or the workflow export.
4. Assign that credential to the `Query Local RAG` node and run the workflow
   manually. A healthy result is grounded and includes citations.
5. Only after manual verification, use this workflow as a sub-workflow of the
   daily health digest.
## Verification

```bash
./scripts/verify-openclaw-integrations
```

This command validates local configuration and service state only. It does not
send a Slack, Discord, Telegram, or n8n webhook test. Perform a deliberate
end-to-end notification test after confirming the destination channel.
