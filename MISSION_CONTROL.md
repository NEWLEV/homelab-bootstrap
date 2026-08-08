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
