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
tailscale serve --https=443 --set-path=/n8n http://127.0.0.1:5678
./homelab-bootstrap/services/integrations/scripts/install-integration-dispatcher.sh
```

Import the required workflow export into n8n and activate it before adding its
local webhook endpoint to `~/.config/aisha/integration-dispatcher.env`. Start
the dispatcher timer only after that step. This prevents alerts from being sent
to an unconfigured or unintended endpoint.

## Verification

```bash
./scripts/verify-openclaw-integrations
```

This command validates local configuration and service state only. It does not
send a Slack, Discord, Telegram, or n8n webhook test. Perform a deliberate
end-to-end notification test after confirming the destination channel.
