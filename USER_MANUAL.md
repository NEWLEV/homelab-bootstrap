# Aisha User Manual

## Table of Contents

1. [Most Common Tasks](#most-common-tasks)
2. [Start Here](#start-here)
3. [Command Reference](#command-reference)
4. [What Aisha Is](#what-aisha-is)
5. [Who This Manual Is For](#who-this-manual-is-for)
6. [Main Concepts](#main-concepts)
7. [Platform Endpoints](#platform-endpoints)
8. [Runbook](#runbook)
9. [How To Use The Docs](#how-to-use-the-docs)
10. [Troubleshooting](#troubleshooting)
11. [Operator Checklist](#operator-checklist)
12. [Status](#status)

## Most Common Tasks

### Validate the bootstrap manifest

```bash
python -m bootstrap --validate
```

### Print the bootstrap plan

```bash
python -m bootstrap --plan
```

### Print the dependency graph

```bash
python -m bootstrap --graph
```

### Show the AI platform plan

```bash
python -m bootstrap --ai-platform
```

### Generate the bootstrap bundle

```bash
python -m bootstrap --bundle
```

### Run the core test slice

```bash
python -m pytest tests/test_app_platform.py tests/test_bootstrap_ai_platform.py tests/test_bootstrap_readiness.py -q
```

## Start Here

Use this decision tree when you are not sure where to begin:

- If you want to start the dashboard app, run `./run-dashboard.sh` from the repo root or use `python -m app --host 0.0.0.0 --port 8000`.
- If you want to confirm the infrastructure state, run `python -m bootstrap --validate`.
- If you want to inspect the bootstrap stack, run `python -m bootstrap --plan` or `python -m bootstrap --graph`.
- If you want the operator view, open `http://aisha:8000/platform/web-dashboard` in your browser, or use the Tailscale IP `http://100.106.201.14:8000/platform/web-dashboard` if `aisha` does not resolve correctly.
- If you want the full platform surface, browse the `/platform` endpoints listed below or use the API explorer at `http://127.0.0.1:8000/docs`.
- If a test is failing, start with the focused suite in [Most Common Tasks](#most-common-tasks).
- If you are trying to understand the system design, read [AISHA_ROADMAP.md](/C:/Users/ZBook/Documents/Aisha/AISHA_ROADMAP.md) first.

## First 10 Minutes

1. Open the operator dashboard in your browser: `http://aisha:8000/platform/web-dashboard` or `http://100.106.201.14:8000/platform/web-dashboard`.
2. Check the API surface in the browser docs at `http://127.0.0.1:8000/docs` if the server is running.
3. Review the live platform pages:
   - http://127.0.0.1:8000/platform/summary
   - http://127.0.0.1:8000/platform/status
   - http://127.0.0.1:8000/platform/personal-os
4. Use the terminal for bootstrap checks and app startup:
   - python -m bootstrap --validate
   - python -m bootstrap --plan
   - python -m bootstrap --ai-platform
   - ./run-dashboard.sh
   - systemctl --user start aisha-local-rag.service
5. If something is off, jump to [Troubleshooting](#troubleshooting).

## Command Reference

| Command | Use |
| --- | --- |
| `python -m bootstrap --validate` | Validate the infrastructure manifest and dependencies |
| `python -m bootstrap --plan` | Print the rendered bootstrap plan |
| `python -m bootstrap --graph` | Print the service dependency graph |
| `python -m bootstrap --storage-network` | Show storage and networking planning |
| `python -m bootstrap --monitoring` | Show monitoring planning |
| `python -m bootstrap --backup-plan` | Show backup and restore planning |
| `python -m bootstrap --ai-platform` | Show the AI platform plan |
| `python -m bootstrap --bundle` | Write the bootstrap artifact bundle |
| `python -m bootstrap.prep --help` | Show prep helper usage |
| `python -m pytest tests/test_app_platform.py tests/test_bootstrap_ai_platform.py tests/test_bootstrap_readiness.py -q` | Run the core verification slice |
| `./run-dashboard.sh` | Start the dashboard app from the repo root |
| `http://aisha:8000/` | Open the dashboard root redirect |
| `http://100.106.201.14:8000/` | Open the dashboard root redirect over Tailscale if needed |
| `http://aisha:8000/platform/web-dashboard` | Open the dashboard operator page |
| `http://100.106.201.14:8000/platform/web-dashboard` | Open the dashboard over Tailscale if the hostname does not resolve |
| `systemctl --user start aisha-local-rag.service` | Start the local RAG service safely on Aisha |
| `systemctl --user status aisha-local-rag.service` | Check whether local RAG is active and enabled |
| `systemctl --user enable aisha-dashboard.service` | Enable the dashboard app to start automatically on boot |
| `systemctl --user start aisha-dashboard.service` | Start the dashboard app immediately |
| `http://127.0.0.1:8000/platform/runbook` | Open the dashboard runbook |
| `python -m app --host 0.0.0.0 --port 8000` | Start the dashboard app directly from Python |

## What Aisha Is

Aisha is a private AI operating platform for a self-hosted workspace. It combines:

- bootstrap and infrastructure management
- local retrieval and knowledge search
- AI platform and agent platform planning
- automation and operations tooling
- a personal operating surface for day-to-day use

This repository is the source of truth for the system design, platform helpers, and test coverage.

## Who This Manual Is For

Use this guide if you want to:

- understand what the project does
- run the bootstrap and platform helpers
- inspect the available API surfaces
- work with the roadmap and integrations plan
- troubleshoot the most common repository-level issues

## Quick Start

1. Read the roadmap: [`AISHA_ROADMAP.md`](/C:/Users/ZBook/Documents/Aisha/AISHA_ROADMAP.md)
2. Review the bootstrap entry point: [`bootstrap/README.md`](/C:/Users/ZBook/Documents/Aisha/bootstrap/README.md)
3. Inspect the repo index: [`ROOT_INDEX.md`](/C:/Users/ZBook/Documents/Aisha/ROOT_INDEX.md)
4. Use the most common tasks above for the usual day-to-day entry points.

## Main Concepts

### Bootstrap

Bootstrap is the infrastructure foundation. It covers:

- manifest validation
- dependency ordering
- storage and networking planning
- monitoring and backup planning
- reverse proxy, DNS, and TLS planning
- bundle generation and readiness reporting

### Platform

The platform layer exposes structured planning surfaces for:

- AI services
- local RAG
- integrations
- skills
- agent platform
- memory
- productivity
- automation
- diagnostics and self-healing
- personal OS views

### Personal OS

The personal OS layer is the unified surface for the system. It combines:

- unified web interface
- conversational system management
- long-term memory
- knowledge graph
- personal productivity
- development assistant
- research assistant
- infrastructure assistant
- home automation integration

## Common Tasks

Additional bootstrap commands:

```bash
python -m bootstrap --storage-network
python -m bootstrap --monitoring
python -m bootstrap --backup-plan
python -m bootstrap.prep --help
```

The prep helper validates the manifest and writes bootstrap artifacts to disk.

## Platform Endpoints

The application exposes several structured endpoints under `/platform`.

Useful examples:

- `/platform/summary`
- `http://127.0.0.1:8000/platform/status`
- `http://127.0.0.1:8000/platform/integrations`
- `http://127.0.0.1:8000/platform/services`
- `http://127.0.0.1:8000/platform/infrastructure`
- `http://127.0.0.1:8000/platform/storage-network`
- `http://127.0.0.1:8000/platform/monitoring`
- `http://127.0.0.1:8000/platform/backups`
- `http://127.0.0.1:8000/platform/exposure`
- `http://127.0.0.1:8000/platform/dns-tls`
- `http://127.0.0.1:8000/platform/rag-api`
- `http://127.0.0.1:8000/platform/ingestion`
- `http://127.0.0.1:8000/platform/local-rag`
- `http://127.0.0.1:8000/platform/skills`
- `http://127.0.0.1:8000/platform/agent-platform`
- `http://127.0.0.1:8000/platform/memory`
- `http://127.0.0.1:8000/platform/persistent-memory`
- `http://127.0.0.1:8000/platform/knowledge-graph`
- `http://127.0.0.1:8000/platform/home-automation`
- `http://127.0.0.1:8000/platform/productivity`
- `http://127.0.0.1:8000/platform/assistant-modes`
- `http://127.0.0.1:8000/platform/external-integrations`
- `http://127.0.0.1:8000/platform/workflow-engine`
- `http://127.0.0.1:8000/platform/task-execution`
- `http://127.0.0.1:8000/platform/autonomous-ops`
- `http://127.0.0.1:8000/platform/repair-guide`
- `http://127.0.0.1:8000/platform/maintenance`
- `http://127.0.0.1:8000/platform/self-healing`
- `http://127.0.0.1:8000/platform/diagnostics`
- `http://127.0.0.1:8000/platform/operations-summary`
- `http://127.0.0.1:8000/platform/personal-os`
- `http://127.0.0.1:8000/platform/web-interface`
- `http://127.0.0.1:8000/platform/web-dashboard`
- `http://127.0.0.1:8000/platform/conversational-management`

The HTML dashboard at `http://127.0.0.1:8000/platform/web-dashboard` is the fastest visual entry point for the personal OS surface. It is a browser-based operator UI with summary cards, sections, memory, operations, integrations panels, and read-only command snippets.

## How To Use The Docs

### `AISHA_ROADMAP.md`

Use the roadmap to understand the full system story and the major layers of the project.

### `INTEGRATIONS_PLAN.md`

Use the integrations plan to understand how n8n, MCP, Skills, GitHub automation, browser automation, and notifications fit together.

### `bootstrap/README.md`

Use the bootstrap README as the operational guide for bootstrap commands, artifacts, and the dashboard launcher.

### `homelab-bootstrap/services/local-rag/README.md`

Use the local-RAG README for the safe boot service, the user-level systemd unit, and the manual launch command on Aisha.

### `ROOT_INDEX.md`

Use the root index to find the main code and helper assets quickly.

## Runbook

Use the dashboard runbook when you need the exact commands for Aisha. It is available at `http://127.0.0.1:8000/platform/runbook` and mirrors the safe boot path for local RAG.

The dashboard service helper installs `aisha-dashboard.service` so the operator UI can start automatically on boot. It binds to `0.0.0.0` so the browser can reach it over Tailscale, and the app root now redirects to the dashboard page.

The dashboard itself is read-only. It shows the commands to run, quick links to docs, and operational status, but it does not execute remote actions.

If `aisha` resolves to the wrong address on Windows, use the Tailscale IP `100.106.201.14` or add a hosts override for `aisha` that points to it.

### Symptom: tests fail immediately

Run the focused suite first:

```bash
python -m pytest tests/test_app_platform.py tests/test_bootstrap_ai_platform.py tests/test_bootstrap_readiness.py -q
```

Then inspect the exact assertion text and check the matching helper in `bootstrap/` or the matching route in `app/main.py`.

### Symptom: bootstrap output looks stale

Regenerate the bundle and report:

```bash
python -m bootstrap --bundle
python -m bootstrap.prep
```

### Symptom: the dashboard or route you need is hard to find

Search the route or helper name:

```bash
rg -n "platform_|render_.*plan|build_.*plan" app bootstrap
```

### Symptom: the manual or docs seem out of sync

Check the roadmap, the bootstrap README, and the root index together. They are the fastest indicators of whether the repository view and the platform view still match.

## Operator Checklist

- confirm the manifest before making infrastructure changes
- keep changes test-backed
- prefer repository-managed config over hidden local state
- use approval gates for destructive or externally visible actions
- update the roadmap or docs when the behavior changes

## Status

This manual reflects the current repository state and the implemented platform surfaces checked into the workspace.









