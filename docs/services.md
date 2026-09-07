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

The default Compose project runs one required RAG API container:

- `local-rag-api` serves the canonical homelab repository knowledge source on
  loopback port `8090`.

The optional `nlc` Compose profile adds `local-rag-nlc-api`, which serves
curated NLC/OpenClaw operating knowledge on loopback port `8091`. The optional
API shares the local Ollama runtime and bearer-token secret, but uses a separate
Chroma store so the general homelab index and NLC operating index can be rebuilt
independently.

Configuration

```
/srv/data/services/local-rag/
```

Knowledge source

```text
/srv/data/git/homelab-bootstrap-index
```

NLC knowledge source

```text
${AISHA_NLC_SOURCE:-/home/nlc/.openclaw/workspace}
```

Enable the optional NLC collection only on hosts that have the source checkout:

```bash
docker compose -f compose/ai/local-rag.yml --profile nlc up -d
```

When Hermes should use this optional collection, set:

```text
HERMES_NLC_RAG_URL=http://local-rag-nlc-api:8080
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

## OpenClaw and Aisha

Purpose

Native OpenClaw provides the Control UI. The repository-managed Aisha
container provides the chat interface and conversation API used by the
dashboard.

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

The native OpenClaw Control UI is served at
`https://aisha.tail4553c9.ts.net/openclaw/` by Tailscale Serve directly to
the host gateway on `127.0.0.1:18789`. The Aisha container is served at
`https://aisha.tail4553c9.ts.net/aisha/` through Traefik. Questions are
forwarded to the Local RAG `/ask/stream` endpoint with the bearer token held
server-side, and answers stream back over SSE with grounded citations.
Conversations persist under `/srv/data/services/openclaw/conversations`.

The dashboard launcher assets live in `configs/homepage/` and are installed
with:

```bash
./scripts/install-homepage-aisha-launcher
```

Homepage control shortcuts

The Homepage dashboard now includes a shortcut panel with working links to
the secure OpenClaw UI at `/openclaw/`, Hermes, Kuma, File Browser, Portainer,
Netdata, and the Aisha chat surface. Mission Control remains `coming soon`
until a standalone page is implemented. The shortcut wiring lives in
`configs/homepage/custom.js` and `configs/homepage/custom.css`. The main
dashboard cards live in `configs/homepage/services.yaml`, which now includes a
live Hermes card that points at the Hermes dashboard.

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

## Hermes

Purpose

Second assistant runtime for experiments and alternate workflows.

Implementation

```
compose/ai/hermes.yml
services/hermes/
docs/hermes.md
```

Hermes is intentionally separate from OpenClaw. It reuses approved homelab
services such as Local RAG and selected MCP servers while keeping its own
memory, skills, sessions, config, and dashboard under `~/.hermes/` or the
host runtime directory under `/srv/data/services/hermes/`.

Hermes can also inspect the OpenClaw checkout through the read-only mount at
`/workspace/openclaw`, which keeps the two runtimes coordinated without
sharing write access.

Hermes state lives under `/srv/data/services/hermes/`, so the normal
service-data backup and restore flow applies to it alongside the rest of the
appliance.

Hermes does not share OpenClaw secrets or browser-delivered code. The live
runtime is installed with:

```bash
bash scripts/install-hermes-service.sh
```

The dashboard is exposed on `http://aisha:9119/`, and the API server listens
on `http://aisha:8642/` once the runtime is started. Both ports bind only to
the Tailscale IPv4 address.

Verify

```bash
docker compose -f compose/ai/hermes.yml config --quiet
```

The HTTPS ingress is configured separately and persistently with:

```bash
sudo bash scripts/configure-tailscale-ingress
```

For a complete AI ingress reconciliation, including service recreation and
health verification, use:

```bash
sudo bash scripts/reconfigure-ai-ingress
```

After the service is installed, verify the runtime with:

```bash
docker compose -f compose/ai/hermes.yml ps
curl -I http://aisha:9119/
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

## n8n and Ollama

For direct Ollama calls from n8n, use the Docker-network hostname:

```text
http://local-rag-ollama:11434
```

Avoid `http://aisha:11434`, `::1:11434`, `127.0.0.1:11434`, and the Tailscale IP
from inside n8n containers. See:

- [n8n Ollama notes](./n8n-ollama-fix.md)
- [Ollama connectivity test workflow](./ollama-connectivity-test.workflow.json)

---

## Bootstrap validation fails

Run:

```bash
./install.sh --list

./install.sh --dry-run
```

Resolve all reported validation errors before applying changes.

