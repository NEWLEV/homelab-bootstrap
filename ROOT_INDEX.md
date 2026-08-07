# Root Index

This workspace contains a mix of source code, test helpers, and patch artifacts from the project work.

## Source Code

- [`app/`](/C:/Users/ZBook/Documents/Aisha/app)
- [`confidence-stage/`](/C:/Users/ZBook/Documents/Aisha/confidence-stage)
- [`homelab-bootstrap/`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap)

## Workspace Notes

- [`WORKSPACE_NOTES.md`](/C:/Users/ZBook/Documents/Aisha/WORKSPACE_NOTES.md)
- [`pytest.ini`](/C:/Users/ZBook/Documents/Aisha/pytest.ini)
- [`run-dashboard.sh`](/C:/Users/ZBook/Documents/Aisha/run-dashboard.sh)
- [`homelab-bootstrap/services/dashboard/README.md`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard/README.md)
- [`app/__main__.py`](/C:/Users/ZBook/Documents/Aisha/app/__main__.py)
- [`homelab-bootstrap/services/local-rag/systemd/aisha-local-rag.service`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/local-rag/systemd/aisha-local-rag.service)
- [`homelab-bootstrap/services/local-rag/scripts/install-local-rag-service.sh`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/local-rag/scripts/install-local-rag-service.sh)
- [`homelab-bootstrap/services/local-rag/scripts/run-local-rag.sh`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/local-rag/scripts/run-local-rag.sh)
- [`homelab-bootstrap/services/local-rag/README.md`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/local-rag/README.md)
- [`homelab-bootstrap/services/dashboard/README.md`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard/README.md)
- [`homelab-bootstrap/services/dashboard/scripts/install-dashboard-service.sh`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard/scripts/install-dashboard-service.sh)
- [`homelab-bootstrap/services/dashboard/scripts/run-dashboard.sh`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard/scripts/run-dashboard.sh)
- [`homelab-bootstrap/services/dashboard/systemd/aisha-dashboard.service`](/C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard/systemd/aisha-dashboard.service)
- [`USER_MANUAL.md`](/C:/Users/ZBook/Documents/Aisha/USER_MANUAL.md)
- [`bootstrap/README.md`](/C:/Users/ZBook/Documents/Aisha/bootstrap/README.md)
- [`.gitignore`](/C:/Users/ZBook/Documents/Aisha/.gitignore)

## Test and Smoke Helpers

- `authenticated-*.py`
- `resource-control-smoke.py`
- `test-*.py`
- `diagnose-*.py`
- `*.json` request fixtures
- `local-rag-*.patch` and `metrics-*.patch` related helpers

## Patch Artifacts

- `auth-*.patch`
- `confidence-*.patch`
- `evaluation-*.patch`
- `fix-*.patch`
- `harden-*.patch`
- `index-*.patch`
- `integrate-*.patch`
- `integrity-*.patch`
- `metrics-*.patch`
- `pass-*.patch`
- `refresh-*.patch`
- `reranker-*.patch`
- `resource-controls-*.patch`
- `snapshot-*.patch`
- `structure-*.patch`
- `test-*.patch`
- `tighten-*.patch`
- `update-*.patch`

## Notes

- The workspace-level pytest configuration uses importlib mode to avoid duplicate test module name collisions.
- Generated cache directories are ignored by `.gitignore`.






