# FileBrowser Quantum

The File Browser service uses FileBrowser Quantum at port `8080`. Its service
identity runs as the host user `nlc` (UID/GID `1000`) and presents two sources:

- `/srv`: writable service and data storage.
- `/openclaw-workspace`: read-only shared workspace containing OpenClaw
  documents, research, memory, and skills.

The workspace source intentionally excludes `~/.openclaw/openclaw.json`,
provider credentials, and agent databases.

## Install or update

```bash
scripts/install-filebrowser-quantum
docker compose -f compose/core/filebrowser.yml up -d --force-recreate filebrowser
```

Quantum stores its own configuration and database under
`/srv/data/services/filebrowser-quantum/data`. The old File Browser database at
`/srv/data/services/filebrowser/database` remains untouched for rollback.

On first sign-in, change the default Quantum administrator password immediately.
