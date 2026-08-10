# Architecture

## Repository layout

```
configs/
docs/
scripts/
scripts/bootstrap.d/
services/
tests/
install.sh
```

---

## Bootstrap workflow

```
install.sh
        │
        ▼
Preflight validation
        │
        ▼
Load bootstrap manifest
        │
        ▼
Validate manifest
        │
        ▼
Discover enabled phases
        │
        ▼
Execute phases in order
        │
        ▼
Restore runtime secrets (optional)
        │
        ▼
Summary
```

---

## Design principles

- Declarative bootstrap manifest
- Idempotent bootstrap scripts
- Repository-managed configuration
- Encrypted runtime secrets
- Automated validation
- Continuous integration

---

## Knowledge source boundary

Local RAG indexes a detached, read-only Git worktree at
`/srv/data/git/homelab-bootstrap-index`. The worktree is pinned to an explicit
40-character commit SHA by `scripts/sync-knowledge-source`; branch names, tags,
implicit latest revisions, and dirty worktrees are rejected.

The detached worktree separates reviewed repository knowledge from operator
changes in the primary checkout. It is reproducible generated state and is
therefore excluded from Restic. The canonical repository and its Git history
remain covered by the normal repository backup path.
