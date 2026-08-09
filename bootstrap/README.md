# Bootstrap

This package contains the infrastructure bootstrap path for Aisha and the planning helpers that span infrastructure, AI platform, agent platform, autonomous operations, personal OS, and integrations surfaces.

## Files

- [`infrastructure.yaml`](./infrastructure.yaml): repo-backed infrastructure manifest
- [`infrastructure.schema.json`](./infrastructure.schema.json): machine-readable manifest schema
- [`infrastructure.schema.md`](./infrastructure.schema.md): human-readable manifest spec
- [`executor.py`](./executor.py): ordered infrastructure phase execution
- [`graph.py`](./graph.py): service dependency graph helpers
- [`backup.py`](./backup.py): backup and restore planning helpers
- [`storage_network.py`](./storage_network.py): storage and networking planning helpers
- [`monitoring.py`](./monitoring.py): monitoring planning helpers
- [`exposure.py`](./exposure.py): reverse-proxy, DNS, and TLS planning helpers
- [`readiness.py`](./readiness.py): Phase 2 readiness summary helpers
- [`ai_platform.py`](./ai_platform.py): AI platform planning helpers
- [`bundle.py`](./bundle.py): bootstrap artifact bundle writer
- [`cli.py`](./cli.py): command-line interface for validation, rendering, graphing, bundling, readiness, and execution
- [`report.py`](./report.py): structured bootstrap summary
- [`prep.py`](./prep.py): one-command bootstrap preparation helper

## Platform Notes

- local RAG now includes a persistent vector storage plan
- embeddings and retrieval should be restored from durable storage before resuming queries
- the dashboard app is launched with `./run-dashboard.sh` from the repo root or with `python -m app`; the service helper binds it on `0.0.0.0` so it is reachable over Tailscale and the root `/` redirects to the dashboard page
- the Mission Control dashboard is the operational surface for agent activity, approvals, and vitals
- the Mission Control service wrapper lives in `homelab-bootstrap/services/mission-control/` and mirrors the dashboard launcher pattern
- the Mission Control SQLite database lives on the `mission-control-data` volume and is included in the backup plan
- the first external notification path is Slack via n8n using `scripts/slack_alerts_n8n_export.json`
- the dashboard runbook is exposed at `http://aisha:8000/platform/runbook`
- the local RAG service is installed and enabled through the `homelab-bootstrap/services/local-rag/` service scripts

## CLI Modes

Run the CLI as a module:

```bash
python -m bootstrap --help
```

Available modes:

- `--schema`: print the manifest schema
- `--validate`: validate the manifest and phase order
- `--plan`: print the rendered bootstrap plan
- `--graph`: print the service dependency graph
- `--storage-network`: print the storage and networking plan
- `--monitoring`: print the monitoring plan
- `--exposure`: print the reverse-proxy and exposure plan
- `--dns-tls`: print the DNS and TLS plan
- `--backup-plan`: print the backup and restore plan
- `--readiness`: print the Phase 2 readiness summary
- `--status`: print the deploy-ready Phase 2 status
- `--ai-platform`: print the Phase 3 AI platform plan
- `--bundle`: write the bootstrap artifact bundle
- `--compose`: print the generated Compose YAML
- `--write-compose`: write the generated Compose YAML to disk
- `--report`: print a structured bootstrap report
- `--write-report`: write the structured bootstrap report to disk
- `--run`: execute the infrastructure phases

## Prep Helper

Run the prep helper as a module:

```bash
python -m bootstrap.prep --help
```

Default behavior:

- validates the manifest
- writes `bootstrap/compose.generated.yaml`
- writes `bootstrap/bootstrap.report.json`

You can also supply explicit paths with flags:

```bash
python -m bootstrap.prep --manifest bootstrap/infrastructure.yaml --compose-output build/compose.yaml --report-output build/report.json
```

Legacy positional arguments are still accepted for compatibility.

## Default Paths

- Manifest: `bootstrap/infrastructure.yaml`
- Compose output: `bootstrap/compose.generated.yaml`
- Report output: `bootstrap/bootstrap.report.json`

## Validation Rules

- service names must be unique
- service dependencies must reference declared services
- service volume references must match declared volumes
- service network references must match declared networks
- top-level `name`, `services`, `volumes`, and `networks` are required
- schema validation runs before manifest parsing

## Current Phase 2 Stack

The checked-in manifest describes the initial infrastructure stack:

- reverse proxy
- monitoring
- Mission Control
- backups
- shared volumes
- internal and edge networks
- explicit monitoring, backup, exposure, and readiness hooks

