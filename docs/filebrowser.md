# File Browser

File Browser is restricted to the directories explicitly mounted by
`compose/core/filebrowser.yml`.

## OpenClaw workspace

The shared OpenClaw workspace is exposed read-only at:

```text
/openclaw-workspace
```

This includes workspace documents, research, memory, and installed skills. It
intentionally does not expose `~/.openclaw/openclaw.json`, gateway credentials,
or agent databases. Use SSH or the OpenClaw CLI for configuration changes.

Apply the change with:

```bash
docker compose -f compose/core/filebrowser.yml up -d --force-recreate filebrowser
```