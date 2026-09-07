# Aisha Homelab Bootstrap

This repository manages a reproducible Linux homelab appliance named Aisha. The
current reference deployment is a Raspberry Pi 5, but GitHub-hosted source,
tests, and documentation should stay portable across supported Linux hosts
unless a file is explicitly documenting the live Aisha machine.

Before starting any task:

1. Check the most recent daily memory note under `workspaces/development/MEMORY.md` for relevant context.
2. Read `LEARNINGS.md` for durable rules and prior decisions that apply to the task.
3. Inspect the current branch and working tree before editing.

The long-term recovery objective for the reference Aisha appliance is:

1. Install a fresh Raspberry Pi OS image.
2. Clone this repository.
3. Run the documented bootstrap process.
4. Restore configuration, services, and persistent data.

Do not claim that one-command recovery is complete unless it has been implemented and validated from a fresh operating-system installation.

## Authoritative Environment

- Host: `aisha`
- Hardware: Raspberry Pi 5 reference deployment; other Debian-family amd64 and
  arm64 Linux hosts are supported bootstrap targets where hardware-specific
  services are not required.
- Operating system: Raspberry Pi OS Lite 64-bit reference deployment; portable
  bootstrap work should target Debian-family Linux.
- Repository root: `/srv/data/git/homelab-bootstrap`
- Knowledge index source: `/srv/data/git/homelab-bootstrap-index`
- Runtime service data root: `/srv/data/services`
- GitHub repository: `NEWLEV/homelab-bootstrap`

Repository-controlled configuration and runtime service data are separate concerns. Configuration, scripts, Compose definitions, tests, and documentation belong in Git. Databases, model files, secrets, caches, and other persistent runtime data belong under `/srv/data/services` unless documented otherwise.

## Project Hierarchy and Versioning

This project has separate version domains:

1. Homelab Bootstrap appliance version.
2. Individual service and component versions.

The appliance version must not be inferred from a component version.

Local RAG currently has its own application version, `0.11.0`, defined in `services/local-rag/app/main.py`.

When changing a component version, update only that component unless the task explicitly includes an appliance release.

## Working Rules

Before editing:

- Inspect the repository and relevant files.
- Confirm the current branch and working-tree state.
- Treat the current repository contents as authoritative.
- Preserve unrelated changes.
- Keep the task narrowly scoped.

During implementation:

- Prefer small, reviewable changes.
- Make shell scripts idempotent.
- Use strict shell error handling where appropriate.
- Log meaningful actions.
- Preserve backward compatibility unless explicitly approved.
- Avoid speculative abstractions.
- Avoid broad reorganizations during feature work.
- Document operational behavior changes.
- Add or update tests for new behavior.
- Use deterministic helper functions where practical.

After implementation:

- Review the complete diff.
- Run validation relevant to the modified files.
- Report validation performed.
- Report validation not performed.
- Report known risks and follow-up work.
- Report current Git status.

## Safety Rules

- Never run development work as root.
- Avoid unnecessary `sudo`.
- Never expose or commit secrets.
- Never commit `.env` files, private keys, API tokens, credentials, or backup passwords.
- Never modify live runtime data unless explicitly required.
- Avoid destructive filesystem operations.
- Obtain approval before destructive operations.
- Never discard uncommitted work.
- Never force-push.
- Never push, merge, tag, publish releases, or close GitHub issues without approval.
- Never claim validation that was not actually performed.

## Branch and Git Workflow

- Start from a clean, up-to-date `main` branch.
- Create a task-specific branch.
- Do not automatically pull when local changes exist.
- Inspect `git diff` before committing.
- Run relevant validation before committing.
- Use clear, narrowly scoped commit messages.
- Stop before push, merge, or tagging unless requested.

## Baseline Validation

General:

```bash
git diff --check
git status --short

```

Shell:

```bash
bash -n path/to/script.sh
```

Use ShellCheck when available.

Local RAG Python:

```bash
python3 -m py_compile \
  services/local-rag/app/main.py \
  services/local-rag/app/indexer.py \
  services/local-rag/app/retrieval.py
```

Local RAG tests:

```bash
docker compose \
  -f compose/ai/local-rag.yml \
  run --rm api \
  pytest tests -q
```

Compose validation:

```bash
docker compose \
  -f compose/ai/local-rag.yml \
  config --quiet
```

Replace placeholder paths with actual filenames before running commands.

## Local RAG Context

Current architecture includes:

- FastAPI
- ChromaDB
- Ollama embeddings and generation
- Hybrid retrieval
- Optional reranking
- Retrieval diagnostics
- Evaluation suite
- Grounded citations
- Confidence policy
- Streaming responses
- Bounded conversation history
- Index job control
- Index integrity
- Metrics
- Bearer-token authentication
- Rate limiting
- Concurrency controls
- Request size limits
- Localhost-only production API

Current repository code always takes precedence over historical plans.

## Coding Preferences

- Prefer complete, syntactically valid files over partial replacements.
- Keep comments concise.
- Avoid broad reorganizations during feature work.
- Reuse the existing stack where practical.
- Preserve API compatibility unless explicitly approved.
- Include validation commands with implementation work.

## Completion Report

Every completed task should include:

- Files changed
- Behavior changed
- Validation performed
- Validation not performed
- Known risks or follow-up work
- Current Git status
