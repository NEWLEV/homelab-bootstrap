# Services

## Purpose

This document describes the services managed by the Aisha homelab,
their purpose, startup method, configuration, and verification
procedures.

---

# Service Management

Services are managed using one of the following mechanisms:

- systemd
- Docker Compose

Bootstrap configures each service but does not necessarily start every
optional workload.

---

# Installed Services

## Docker

Purpose

Container runtime for application services.

Verify

```bash
systemctl status docker

docker info
```

---

## Local RAG

Purpose

Provides local document indexing and retrieval.

Configuration

```
/srv/data/services/local-rag/
```

Secrets

```
/srv/data/services/local-rag/secrets/
```

Verify

```bash
docker compose ps

python -m pytest tests -q
```

---

## Restic

Purpose

Encrypted backups.

Configuration

```
~/.config/restic/
```

Verify

```bash
restic snapshots
```

---

## OpenClaw

Purpose

Gateway for the local assistant runtime. Hosts the Aisha chat interface
and conversation API used by the dashboard.

Implementation

```
compose/ai/openclaw.yml
services/openclaw/
```

Runtime contract

```
services/openclaw/start.sh
services/openclaw/server.js
services/openclaw/Dockerfile
```

Aisha chat

The gateway serves the Aisha chat UI and API at
`https://aisha.tail4553c9.ts.net/aisha/`, same-origin with the Homepage
dashboard. Questions are forwarded to the Local RAG `/ask/stream` endpoint
with the bearer token held server-side, and answers stream back over SSE
with grounded citations. Conversations persist under
`/srv/data/services/openclaw/conversations`.

The shared dashboard launcher assets live in `configs/homepage/`. The Python
platform dashboard serves them directly from `/platform/assets/`, while the
Homepage container receives them with:

```bash
./scripts/install-homepage-aisha-launcher
```

Stock OpenClaw Control UI

The upstream OpenClaw Control UI remains available separately from the Aisha
chat surface. The dashboard exposes a convenience route at `/openclaw/`, which
redirects to the stock Control UI on the secure Tailscale URL. The default
point is `https://aisha.tail4553c9.ts.net/openclaw/`, and the target can be
overridden with `OPENCLAW_CONTROL_UI_URL` if you need a different host.

The secure path avoids the device-identity errors that appear over plain HTTP.

Configuration

```
/srv/data/services/openclaw/
/srv/data/services/openclaw/config/
```

Secrets

```
/srv/data/services/openclaw/secrets.env
/srv/data/services/local-rag/secrets/api-token
```

Verify

```bash
scripts/install-openclaw-runtime
./install.sh --validate-manifest
./tests/aisha-chat.sh
node --test services/openclaw/test/gateway.test.js
docker compose -f compose/ai/openclaw.yml config --quiet
```

---

# Starting Services

Example:

```bash
docker compose up -d
```

or

```bash
systemctl start <service>
```

---

# Stopping Services

```bash
docker compose down
```

or

```bash
systemctl stop <service>
```

---

# Updating Services

1. Pull repository updates.

```bash
git pull --ff-only
```

2. Run a dry run.

```bash
./install.sh --dry-run
```

3. Apply bootstrap changes if required.

```bash
./install.sh --apply
```

4. Restart affected services.

---

# Verifying Service Health

Check for failed system services:

```bash
systemctl --failed
```

List running containers:

```bash
docker compose ps
```

Inspect Docker:

```bash
docker info
```

Review installer logs:

```bash
ls /srv/data/logs/bootstrap/
```

---

# Troubleshooting

## Service will not start

Review:

```bash
journalctl -u <service>
```

---

## Docker container exits

Inspect:

```bash
docker compose logs
```

---

## Missing secrets

Restore runtime secrets:

```bash
./install.sh --restore-secrets
```

---

## Bootstrap validation fails

Run:

```bash
./install.sh --list

./install.sh --dry-run
```

Resolve all reported validation errors before applying changes.
---

## Slack integration

The first supported external chat integration path is outbound Slack
notifications through n8n, not a native Slack bot inside OpenClaw.

- Import `scripts/slack_alerts_n8n_export.json` into n8n.
- Set `SLACK_WEBHOOK_URL` to a Slack Incoming Webhook URL.
- Set `MISSION_CONTROL_PUBLIC_URL` to the Mission Control base URL that your
  operators can reach, for example `https://aisha.tail4553c9.ts.net/mission-control`.
- Post Mission Control approval or alert payloads to the workflow webhook at
  `/webhook/mission-control/slack`.

This keeps Slack as a notification and approval-routing surface while Aisha
and OpenClaw remain the local reasoning and control boundary.

---

## Integration webhooks

Aisha now uses one shared webhook pattern for external alerting integrations.
Users should not have to design each target from scratch.

Available example exports:

- `scripts/slack_alerts_n8n_export.json`
- `scripts/discord_alerts_n8n_export.json`
- `scripts/telegram_alerts_n8n_export.json`
- `scripts/integration_webhooks.sample.json`

Recommended setup flow:

1. choose the target platform
2. create or rotate the platform webhook secret
3. store secrets only in n8n or local runtime environment variables
4. import the matching example export
5. test with the shared Mission Control-shaped payload

Shared payload example:

```json
{
  "title": "Aisha test alert",
  "summary": "Integration webhook check",
  "detail": "This payload shape is shared across Slack, Discord, and Telegram examples.",
  "risk": "low"
}
```



Automatic forwarding helper:

- `scripts/mission_control_webhook_dispatcher.py` polls Mission Control and forwards
  new events and pending approvals to any configured Slack, Discord, or Telegram
  integration webhook endpoint.

The dashboard also exposes an operator-facing setup page at `/platform/integration-webhooks`.

Use `python scripts/seed_mission_control_demo.py` to populate Mission Control with demo events and a pending approval for UI and webhook testing.
