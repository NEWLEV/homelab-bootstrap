# Workspace Notes

- `pytest.ini` uses `--import-mode=importlib` so duplicate test filenames in different subprojects do not collide during collection.
- The root `app/` package exists as a shared compatibility layer for workspace-wide test runs.

- The dashboard app is launched with `./run-dashboard.sh` or `python -m app`; the preferred operator entry point is `http://aisha:8000/platform/web-dashboard` or `http://100.106.201.14:8000/platform/web-dashboard` when Tailscale hostname resolution is not correct. The root `/` path redirects to the dashboard page.
- The dashboard runbook lives at `http://aisha:8000/platform/runbook` and stays read-only so it can display commands without executing remote actions.
- The local RAG service can be installed with `homelab-bootstrap/services/local-rag/scripts/install-local-rag-service.sh` and enabled with `systemctl --user enable aisha-local-rag.service`.

- The dashboard service helper lives under `homelab-bootstrap/services/dashboard/` and installs `aisha-dashboard.service` for local boot auto-start from the repo root. The helper now binds the app on `0.0.0.0` so it can be reached over Tailscale.


