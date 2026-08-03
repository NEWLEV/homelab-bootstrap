# Release Process

## Purpose

This document defines the release workflow for the Aisha homelab project.

The goals are to:

- maintain a stable `main` branch
- keep changes small and reviewable
- ensure all changes are validated before release
- preserve a complete project history

---

# Branching Strategy

The `main` branch always represents the latest stable version of the project.

All development must occur on feature branches.

Examples:

```
feature/bootstrap-manifest
feature/bootstrap-descriptions

fix/local-rag-auth

docs/disaster-recovery

refactor/bootstrap-directory

test/bootstrap-manifest
```

Feature branches should address a single logical change.

---

# Development Workflow

1. Update the local repository.

```bash
git switch main

git pull --ff-only

git fetch --prune
```

2. Create a feature branch.

```bash
git switch -c feature/<name>
```

3. Implement the change.

4. Validate locally.

5. Commit.

6. Push the branch.

7. Open a pull request.

8. Wait for all CI checks to pass.

9. Merge the pull request.

10. Delete the feature branch.

---

# Local Validation

Before committing, run all applicable validation.

## Shell

```bash
bash -n install.sh

shellcheck install.sh
```

Validate bootstrap scripts:

```bash
bash -n scripts/bootstrap.d/*.sh

shellcheck scripts/bootstrap.d/*.sh
```

---

## Bootstrap Manifest

```bash
jq empty configs/bootstrap.json

./tests/bootstrap-manifest.sh
```

---

## Installer

```bash
./install.sh --list

./install.sh --dry-run
```

---

## JSON

```bash
python3 -m json.tool configs/bootstrap.json
```

---

## Docker Compose

Validate every Compose file that was modified.

Example:

```bash
docker compose \
    -f compose/core/homepage.yml \
    config
```

---

## Python

Run the Local RAG test suite when applicable.

```bash
cd services/local-rag

python -m pytest tests
```

---

# Continuous Integration

Every pull request must pass all required GitHub Actions workflows.

Current validation includes:

- Shell validation
- Bootstrap manifest regression tests
- Configuration validation
- Docker Compose validation
- Local RAG test suite

Do not merge changes with failing checks.

---

# Pull Requests

Each pull request should:

- solve one problem
- include validation
- update documentation if required
- avoid unrelated changes

Use a descriptive title.

Example:

```
feat: add bootstrap manifest

fix: validate optional services

docs: add disaster recovery guide

refactor: move bootstrap scripts

test: validate bootstrap manifest
```

---

# Merge Strategy

Merge only after:

- review is complete
- CI passes
- documentation is updated

Use merge commits to preserve branch history.

Delete feature branches after merging.

---

# Post-Merge Verification

After merging:

```bash
git switch main

git pull --ff-only

git fetch --prune
```

Verify:

```bash
git status

git log --oneline --decorate -5
```

Expected:

- clean working tree
- local `main` matches `origin/main`

Remove merged local branches.

```bash
git branch --merged main |
sed 's/^[* ]*//' |
grep -v '^main$' |
xargs -r git branch -d
```

Prune deleted remote branches.

```bash
git fetch --prune
```

---

# Documentation Requirements

Documentation should be updated whenever changes affect:

- installation
- bootstrap
- storage
- networking
- services
- secrets
- disaster recovery
- developer workflow
- release workflow

Documentation is considered part of the implementation.

---

# Release Checklist

Before considering a release complete:

- [ ] Repository is clean.
- [ ] Bootstrap manifest validated.
- [ ] Installer dry run succeeds.
- [ ] ShellCheck passes.
- [ ] Tests pass.
- [ ] CI succeeds.
- [ ] Documentation updated.
- [ ] Pull request merged.
- [ ] Local repository synchronized with `origin/main`.
- [ ] Feature branches removed.

---

# Rollback

If a release introduces problems:

1. Identify the offending commit.

```bash
git log --oneline
```

2. Revert the change.

```bash
git revert <commit>
```

3. Push the revert.

4. Open a pull request.

5. Allow CI to validate the rollback.

Avoid rewriting published history.

---

# Design Principles

The release process emphasizes:

- small, focused changes
- repeatable validation
- automated testing
- infrastructure as code
- complete documentation
- stable releases
