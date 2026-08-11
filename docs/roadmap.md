# Aisha Platform Roadmap

## Vision

Aisha is a private, self-hosted AI operating platform. Its durable state is
repository-managed, reviewable, reproducible, and recoverable from bare metal.

The governing principles are reproducibility, determinism, modularity,
observability, security, portability, and AI-first operation. Human approval
remains mandatory for destructive or externally visible actions.

## Authority and provenance

This document is authoritative on `main`. It selectively promotes the useful
scope from the historical, unrelated `master` prototype without importing that
branch's generated artifacts, test databases, patches, or unsupported claims.
The historical reference is commit `47e67ff`.

## Platform layers

| Layer | Objective | Baseline status |
| --- | --- | --- |
| Operating system | Deterministic bare-metal installation and recovery | Partial |
| Infrastructure | Storage, Docker, networking, TLS, monitoring, and backups | Partial |
| Secrets | One encrypted source of truth with reproducible restoration | Partial |
| Knowledge | Private ingestion, indexing, provenance, and retrieval | Partial |
| Local RAG | Grounded local retrieval and generation | Deployed |
| OpenClaw | Tool-using agent runtime with approval gates | Deployed with drift |
| Agent system | Role-scoped cooperating agents | Deployed, least privilege pending |
| Memory | Searchable durable operational and personal context | Partial |
| Automation | Durable workflows, retries, schedules, and approvals | Partial; n8n absent |
| Observability | Metrics, health, logs, alerts, and action events | Partial |
| Development platform | GitHub, tests, CI, review, and releases | Partial |
| Multi-model AI | Task-aware model and tool routing | Planned |
| Voice | Speech input, output, and safe system interaction | Planned |
| Home integration | Home Assistant, MQTT, sensors, and robotics | Planned |
| Self-maintenance | Drift detection and approval-gated remediation | In progress |

## Current mission order

1. Establish the inventory, drift map, event schema, and approval trail.
2. Reduce network exposure, beginning with the OpenClaw gateway.
3. Consolidate OpenClaw and scope every agent by role and trust boundary.
4. Apply maintenance updates and make storage health observable.
5. Prove local and off-site restores into isolated scratch paths using `docs/backup-restore.md`.
6. Reconcile all remaining services and introduce durable recurring audits.

## Completion rules

- A roadmap item is complete only when repository state, validation, live
  verification, rollback instructions, and backup/restore coverage agree.
- Generated output is evidence, not source configuration.
- Unverified historical claims are not inherited as current facts.
- Remaining drift must be removed or represented by an owned ticket.
