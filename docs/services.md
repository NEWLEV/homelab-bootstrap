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

Verify

```bash
restic snapshots
```

---

## OpenClaw

Purpose

Gateway for the local assistant runtime.

Current scaffold

```
compose/ai/openclaw.yml
services/openclaw/
```

Configuration

```
/srv/data/services/openclaw/
~/.config/openclaw/
```

Secrets

```
~/.config/openclaw/secrets.env
```

Verify

```bash
./install.sh --validate-manifest
./tests/openclaw.sh
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
