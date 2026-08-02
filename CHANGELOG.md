# Changelog

All notable changes to the Aisha Homelab Bootstrap appliance are documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning for appliance releases.

Component versions, including Local RAG, are maintained independently and are not appliance versions.

## [Unreleased]

### Added

- Release and recovery validation work for the Bootstrap Appliance milestone.

## [1.6.0] - Unreleased

### Added

- Top-level bootstrap installer with list, dry-run, apply, logging, and secret-restoration modes.
- Idempotent system bootstrap phase.
- Non-destructive dual-NVMe storage validation.
- Idempotent Docker installation and configuration.
- Central service manifest and appliance validation script.
- SOPS and age encrypted appliance-secret recovery.
- LUKS-encrypted offline recovery-key escrow workflow.
- Disaster-recovery guide.
- Repository architecture decisions covering MCP access, secret escrow, boot storage, vector storage, and notifications.
- Local RAG authentication, resource controls, metrics, integrity checks, job control, streaming, conversation support, evaluation, retrieval diagnostics, reranking, and grounded response controls.

### Changed

- Docker bootstrap now avoids unnecessary configuration rewrites and service restarts.
- Local RAG tests are isolated from production environment settings.
- Restore testing runs with sufficient repository access.
- Repository working and validation guidance is documented in `AGENTS.md`.

### Security

- Runtime credentials can be restored from a Git-tracked SOPS-encrypted bundle.
- The age private key is kept outside Git and escrowed using a password manager and encrypted offline USB.
- Secret restoration refuses unsafe symlink targets and writes files atomically.

### Known limitations

- A complete recovery from a freshly installed operating system has not yet been timed and validated.
- The measured recovery-time objective is pending.
- The release remains blocked until the fresh-install acceptance checks pass.
- OpenClaw Compose deployment remains deferred.
- Traefik is currently optional and may not be running.

## [0.6.0]

Historical appliance milestone predating the Bootstrap Appliance release process.

Earlier historical tags:

- `v0.5-secure-discord`
- `v0.4-multi-agent`
- `v0.3-resilient-platform`
- `v0.2-secure-platform`
- `v0.1-foundation`
