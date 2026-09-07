# MEMORY.md

Use this file for durable long-term memory that should survive across sessions.

## Keep here

- stable preferences
- repeated decisions
- recurring project facts
- lessons that matter later

## Current durable facts

- Hermes can read the OpenClaw checkout from `/workspace/openclaw` via a read-only bind mount.
- Hermes keeps its own runtime state under `/srv/data/services/hermes`.
- The active Hermes branch for the mount fix is `codex-hermes-homepage`.

## Keep out

- secrets
- raw logs
- transient task state

## Format

Write short factual bullets only.
