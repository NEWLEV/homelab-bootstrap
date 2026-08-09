# Mission Control

Mission Control is the lightweight operational dashboard for agent activity, approvals, vitals, and the overnight digest. It is read-first, local-only by default, and never executes actions itself.

## Architecture

- Backend: FastAPI with SQLite persistence
- Frontend: static HTML and vanilla JavaScript
- Realtime updates: Server-Sent Events on `/api/stream`
- Authenticated ingest: `POST /api/events` with `X-Mission-Control-Token`
- Approval workflow: `POST /api/approvals/{id}/approve?confirm=true` and `/reject?confirm=true` only update records and emit events
- The UI never shells out, touches Docker, or mutates infrastructure
- The platform dashboard embeds `/mission-control/`, which proxies to the
  standalone service at `MISSION_CONTROL_URL` (default
  `http://127.0.0.1:8020`)
- Dashboard API references are relative, so the same UI works both standalone
  and through the platform proxy

## Runbook

- Start locally: `python -m mission_control --host 0.0.0.0 --port 8020`
- Service wrapper: `homelab-bootstrap/services/mission-control/`
- Install helper: `homelab-bootstrap/services/mission-control/scripts/install-mission-control-service.sh`
- Health check: `GET /healthz`
- Readiness check: `GET /ready`
- Backup: include the SQLite volume `mission-control-data` in the existing backup plan
- Restore: restore the SQLite file to `/srv/data/services/mission-control-data/mission-control.sqlite3` before restarting the service
- Restore path: if the backup system restores into a staging volume first, copy the SQLite file back into the live volume and restart Mission Control
- Token rotation: update the repo secret that populates `MISSION_CONTROL_TOKEN`, then restart the service
- Demo mode: set `MC_DEMO_SEED=true` only for local evaluation; leave it off in production

## Slack

Mission Control does not send Slack messages directly. The supported first
integration path is an n8n workflow that receives Mission Control-shaped
payloads and posts them to a Slack Incoming Webhook.

- Workflow exports: `scripts/slack_alerts_n8n_export.json`, `scripts/discord_alerts_n8n_export.json`, `scripts/telegram_alerts_n8n_export.json`
- Approval sample: `scripts/mission_control_n8n_export.json`
- Consumer example: `scripts/mission_control_sample_consumer.py`
- Shared config sample: `scripts/integration_webhooks.sample.json`

Recommended payload shape for Slack routing:

```json
{
  "title": "Upgrade Traefik 3.1 -> 3.3",
  "summary": "Roll forward after validation",
  "detail": "Rollback is ready if the health checks fail.",
  "risk": "high",
  "approval_id": "9ecf7a34-7c0d-4e80-a4ef-34aa2f42f918"
}
```

The imported n8n workflow expects:

- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook target
- `MISSION_CONTROL_PUBLIC_URL`: operator-facing base URL for Mission Control

If `approval_id` is present, the workflow includes an approval URL in the
Slack message so an operator can pivot back into the dashboard.

## API

- `POST /api/events`
- `GET /api/events`
- `GET /api/stream`
- `GET /api/approvals`
- `POST /api/approvals/{id}/approve`
- `POST /api/approvals/{id}/reject`
- `GET /api/vitals`
- `GET /api/digest`
- `GET /healthz`


## Automatic forwarding

Use `scripts/mission_control_webhook_dispatcher.py` to poll Mission Control and
forward new events and pending approvals to any enabled integration webhook.

Environment variables:

- `MISSION_CONTROL_URL`
- `MISSION_CONTROL_TOKEN`
- `MISSION_CONTROL_PUBLIC_URL`
- `SLACK_ALERT_WEBHOOK_URL`
- `DISCORD_ALERT_WEBHOOK_URL`
- `TELEGRAM_ALERT_WEBHOOK_URL`
- `INTEGRATION_DISPATCH_ONCE=true` for a single pass

Example:

```bash
INTEGRATION_DISPATCH_ONCE=true python scripts/mission_control_webhook_dispatcher.py
```

Use `python scripts/seed_mission_control_demo.py` to populate Mission Control with demo events and a pending approval for UI and webhook testing.
