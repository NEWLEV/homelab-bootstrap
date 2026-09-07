# AGENTS.md - Workspace Operating Rules

Use this workspace as the current home base.

## Before any task

1. Read the newest daily note under `workspaces/development/MEMORY.md` if one exists.
2. Read `LEARNINGS.md`.
3. Inspect the current branch and working tree before editing.

## Core rules

- Treat the repository contents as authoritative.
- Keep changes small, scoped, and reviewable.
- Preserve unrelated work.
- Avoid destructive actions, history rewrites, and secret exposure.
- Ask before anything external, irreversible, or risky.
- Do not claim validation you did not run.

## Git and delivery

- Start from a clean, up-to-date branch when practical.
- Inspect the diff before committing.
- Run the relevant checks for the files you changed.
- Stop before push, merge, tag, or release unless requested.

## Validation

Run the lightest relevant checks first:

```bash
git diff --check
git status --short
```

Add language- or service-specific tests only when they matter to the change.

## Recovery objective

This project exists to make a fresh Debian-family Linux install clone,
bootstrap, and restore reliably. The live Aisha reference host is a Raspberry
Pi 5, but new repository work should keep amd64 and arm64 Linux portability in
view. Do not claim one-command recovery until it has been validated from a
clean OS installation.
