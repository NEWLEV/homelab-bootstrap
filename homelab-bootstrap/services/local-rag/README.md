# Local RAG Service

This service provides Aisha's local retrieval API and file-backed knowledge surface.

## Start On Aisha

1. Install the user service:

```bash
cd /srv/data/git/homelab-bootstrap/workspaces/development/repo/services/local-rag
./scripts/install-local-rag-service.sh
```

2. Start it manually if needed:

```bash
systemctl --user start aisha-local-rag.service
```

3. Open the service in a browser:

- `http://aisha:8080`
- `http://aisha:8080/files`
- `http://aisha:8080/settings/profile`

## Launcher

Use `./scripts/run-local-rag.sh` to launch the service manually from the service directory after activating the Aisha Python environment if needed.

## Boot Auto-Start

The file `systemd/aisha-local-rag.service` is the user-level systemd unit that can be installed into `~/.config/systemd/user/`.

## Safe Operation

- The service is designed to auto-start safely at boot once enabled for the user.
- The web dashboard only shows read-only command examples for local RAG control.
- Use the dashboard runbook at `http://127.0.0.1:8000/platform/runbook` for the operator-facing command set.
