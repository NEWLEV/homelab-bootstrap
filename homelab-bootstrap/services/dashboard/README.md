# Dashboard Service

This service starts Aisha's main dashboard app automatically for the operator UI.

## Start On Aisha

1. Install the user service:

```bash
cd /srv/data/git/homelab-bootstrap/workspaces/development/repo
./homelab-bootstrap/services/dashboard/scripts/install-dashboard-service.sh
```

2. Start it manually if needed:

```bash
systemctl --user start aisha-dashboard.service
```

3. Open the dashboard in a browser:

- `http://aisha:8000/`
- `http://aisha:8000/platform/web-dashboard`
- `http://aisha:8000/platform/runbook`
- `http://100.106.201.14:8000/platform/web-dashboard`

The root `/` route redirects to the dashboard page so the short URL works in browsers too.

The platform dashboard loads the same repository-managed Aisha chat launcher
as Homepage. The floating `Chat with Aisha` button probes the OpenClaw gateway
at `/aisha` first, which the Python dashboard proxies to OpenClaw, then falls back to port `18789` for direct dashboard access.
The dedicated Mission Control section contains the single
`Open Mission Control` button.

The dashboard proxies `/mission-control/` to the standalone Mission Control
service at `http://127.0.0.1:8020`. Override that target with
`MISSION_CONTROL_URL` if the service moves. Both
`aisha-dashboard.service` and `aisha-mission-control.service` must be
running for live Mission Control data.

## Launcher

Use `./homelab-bootstrap/services/dashboard/scripts/run-dashboard.sh` or `python -m app` from the repository root to launch the dashboard manually.

## Boot Auto-Start

The file `systemd/aisha-dashboard.service` is the user-level systemd unit that can be installed into `~/.config/systemd/user/`. It runs from the repo root, not from the service subdirectory.

## Safe Operation

- The dashboard is read-only and shows commands instead of executing remote actions.
- Use the dashboard runbook for the exact operator commands.
- The service helper binds the dashboard to `0.0.0.0` so it is reachable from a Tailscale-connected browser.
- Keep the manual launcher bound to localhost unless you explicitly need remote access.
- The helper sets `CHROMA_PATH` to a user-writable directory so the app can start cleanly under systemd.

## Related Files

- scripts/install-dashboard-service.sh installs the user-level systemd unit.
- scripts/run-dashboard.sh launches the app manually from the repo root.
- systemd/aisha-dashboard.service is the checked-in unit template.

