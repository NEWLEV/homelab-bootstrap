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

## Launcher

Use `./run-dashboard.sh` or `python -m app` to launch the dashboard manually from the repository root.

## Boot Auto-Start

The file `systemd/aisha-dashboard.service` is the user-level systemd unit that can be installed into `~/.config/systemd/user/`.

## Safe Operation

- The dashboard is read-only and shows commands instead of executing remote actions.
- Use the dashboard runbook for the exact operator commands.
- Keep the dashboard bound to localhost when using the service helper.

## Related Files

- scripts/install-dashboard-service.sh installs the user-level systemd unit.
- scripts/run-dashboard.sh launches the app manually from the repo root.
- systemd/aisha-dashboard.service is the checked-in unit template.

