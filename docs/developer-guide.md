# Developer Guide

## Purpose

This guide describes the development workflow, repository conventions, testing requirements, and contribution process for the Aisha homelab project.

The objectives are to ensure that changes are:

- reproducible
- reviewable
- tested
- documented
- easy to maintain

---

# Repository Structure

```
.
├── compose/
├── configs/
├── docs/
├── monitoring/
├── scripts/
│   └── bootstrap.d/
├── security/
├── services/
├── tests/
├── install.sh
└── .github/
```

Each directory has a single responsibility.

| Directory | Purpose |
|-----------|---------|
| `compose/` | Docker Compose definitions |
| `configs/` | Repository-managed configuration |
| `docs/` | Project documentation |
| `monitoring/` | Monitoring utilities |
| `scripts/` | Operational scripts and bootstrap phases |
| `security/` | Firewall and security configuration |
| `services/` | Service implementations |
| `tests/` | Validation and regression tests |

---

# Development Workflow

Create a feature branch.

```bash
git switch -c feature/<name>
```

Implement the change.

Validate locally.

Commit.

Push.

Open a pull request.

Merge only after all CI checks pass.

---

# Coding Standards

## Shell Scripts

Use Bash.

Include:

```bash
#!/usr/bin/env bash
```

Scripts should:

- be idempotent
- fail immediately on unrecoverable errors
- produce clear log output
- avoid interactive prompts unless required

Validate with:

```bash
bash -n script.sh

shellcheck script.sh
```

---

## JSON

Validate using:

```bash
jq empty file.json

python3 -m json.tool file.json
```

---

## Docker Compose

Validate using:

```bash
docker compose \
    -f compose/<file>.yml \
    config
```

---

## Python

Use Python 3.13.

Run:

```bash
python -m pytest
```

before committing.

---

# Bootstrap Phases

Bootstrap phases are defined in:

```text
configs/bootstrap.json
```

Scripts reside in:

```text
scripts/bootstrap.d/
```

Every phase must define:

- id
- script
- description
- enabled

New phases must be validated with:

```bash
./install.sh --list

./install.sh --dry-run

./tests/bootstrap-manifest.sh
```

---

# Testing

Before opening a pull request, run:

```bash
bash -n install.sh

shellcheck install.sh

./tests/bootstrap-manifest.sh

python -m pytest services/local-rag/tests
```

Resolve all failures before committing.

---

# Continuous Integration

GitHub Actions validates:

- shell scripts
- bootstrap manifest
- JSON configuration
- Docker Compose configuration
- Local RAG tests

Every pull request should pass all checks before merging.

---

# Commit Messages

Use concise, imperative commit messages.

Examples:

```
feat: add bootstrap manifest

fix: validate optional services

refactor: move bootstrap scripts

docs: add disaster recovery guide

test: validate bootstrap manifest
```

---

# Pull Requests

Each pull request should:

- address a single concern
- include testing
- include documentation updates when applicable
- keep changes focused and reviewable

---

# Documentation

Documentation is part of the codebase.

Update documentation whenever changes affect:

- installation
- recovery
- configuration
- services
- networking
- storage
- bootstrap behavior

---

# Review Checklist

Before requesting review:

- [ ] Repository is clean.
- [ ] Installer passes validation.
- [ ] ShellCheck reports no errors.
- [ ] Tests pass.
- [ ] Documentation updated.
- [ ] CI succeeds.
- [ ] Commit messages are clear.

---

# Design Principles

The project follows these principles:

- Declarative configuration
- Idempotent automation
- Infrastructure as code
- Manifest-driven execution
- Secure secret management
- Automated validation
- Small, reviewable changes
- Comprehensive documentation
