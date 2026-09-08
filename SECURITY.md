# Security Policy

This repository contains homelab bootstrap code, documentation, Compose files,
and redacted configuration examples. Runtime secrets, private keys, tokens,
passwords, live databases, model caches, and host-specific `.env` files must not
be committed.

## Reporting a Vulnerability

Do not open a public issue with secrets, tokens, private host details, or
exploit instructions.

Use a private GitHub security advisory when available. If advisories are not
available, contact the repository owner privately and include only the minimum
detail needed to reproduce the issue.

## Public Repository Rules

- Keep examples redacted and non-sensitive.
- Keep runtime state under `/srv/data/services`, not in Git.
- Keep host-specific overrides in untracked env files.
- Rotate any credential that is accidentally committed or exposed.
- Treat encrypted secret bundles as sensitive operational artifacts even when
  they are safe to store in Git.

## Supported Scope

The live reference appliance is Aisha, but the repository is intended to support
Debian-family Linux hosts on `amd64` and `arm64`, plus MacBooks as development
and control machines.
