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

Knowledge source

```text
/srv/data/git/homelab-bootstrap-index
```

Prepare an exact reviewed revision before deploying or indexing:

```bash
./scripts/sync-knowledge-source <40-character-commit-sha>
```

The command refuses symbolic revisions and dirty source state. After the
Local RAG container mounts that worktree, rebuild and verify the index:

```bash
./scripts/index-knowledge
```

The indexing wrapper reads the existing bearer-token file without printing
the token. It requires a clean detached worktree, calls the authenticated
index API, and verifies both job status and index integrity.

Rollback

1. Run `scripts/sync-knowledge-source` with the previously verified commit.
2. Recreate only the Local RAG API container using the repository Compose file.
3. Run `scripts/index-knowledge` and confirm integrity is valid.

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

Canonical backup and restore reference

```text
docs/backup-restore.md
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

The gateway serves the secure OpenClaw Control UI at
`https://aisha.tail4553c9.ts.net/openclaw/` via Tailscale Serve and the Aisha
chat UI at `https://aisha.tail4553c9.ts.net/aisha/`, same-origin with the
Homepage dashboard. Questions are forwarded to the Local RAG `/ask/stream`
endpoint with the bearer token held server-side, and answers stream back over
SSE with grounded citations. Conversations persist under
`/srv/data/services/openclaw/conversations`.

The dashboard launcher assets live in `configs/homepage/` and are installed
with:

```bash
./scripts/install-homepage-aisha-launcher
```

Homepage control shortcuts

The Homepage dashboard now includes a shortcut panel with working links to the
secure OpenClaw UI, Kuma, File Browser, Portainer, Netdata, and the Aisha chat
surface. Mission Control and Pironman5 Max are labeled `coming soon` until
those standalone pages are fully implemented. The shortcut wiring lives in
`configs/homepage/custom.js` and `configs/homepage/custom.css`.

Configuration

```
/srv/data/services/openclaw/
~/.config/openclaw/
```

Secrets

```
~/.config/openclaw/secrets.env
/srv/data/services/local-rag/secrets/api-token
```

Verify

```bash
./install.sh --validate-manifest
./tests/openclaw.sh
./tests/aisha-chat.sh
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
