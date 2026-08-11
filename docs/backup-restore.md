# Backup and Restore

## Purpose

This document is the canonical reference for Aisha backup scheduling, backup
commands, and restore verification. It is intentionally concise so retrieval
can surface it quickly for questions about backup timing or recovery steps.

## Backup schedule

### Local backup

- Script: `scripts/backup`
- Timer: `configs/systemd/aisha-backup.timer`
- Schedule: nightly at `03:15:00`
- Delay: up to `15m` randomized delay
- Retention:
  - keep daily: 7
  - keep weekly: 5
  - keep monthly: 12

### Off-site backup

- Script: `scripts/backup-offsite`
- Timer: `configs/systemd/aisha-backup-offsite.timer`
- Schedule: weekly on Saturday at `04:30:00`
- Delay: up to `30m` randomized delay
- Retention:
  - keep daily: 7
  - keep weekly: 5
  - keep monthly: 12

## What gets backed up

Both jobs back up:

- `/etc`
- `/home/nlc`
- `/srv/data/git`
- `/srv/data/services`

Both jobs exclude transient caches, secrets, and the dedicated knowledge index
source through `configs/restic-excludes.txt`.

## Restore verification

The restore smoke test is:

```bash
scripts/restore-test
```

It restores `README.md` from the latest snapshot into a scratch path and
compares the restored file with the live file.

## Secret restoration

Before restoring services after a fresh install:

```bash
./install.sh --restore-secrets
```

Runtime secrets are stored separately from the backup data and must be restored
before services that depend on them are started.

## Operational notes

- Local backup logs are written under `/srv/data/logs/backups/`.
- Off-site backup logs are written under `/srv/data/logs/backups/`.
- Backups are considered healthy only when the backup job completes and the
  restore test passes.
