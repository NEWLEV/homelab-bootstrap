# ADR 0005: Notification Transport

- Status: Accepted
- Date: 2026-08-01

## Context

Aisha requires reliable notifications for monitoring, backups, validation, updates, and recovery. A locally hosted notification service cannot report that the host itself is offline.

## Decision

- Hosted ntfy.sh is the primary notification transport.
- healthchecks.io provides the external heartbeat.
- All jobs send notifications through a shared `notify.sh` wrapper.
- Notification credentials are stored in the encrypted secrets store.
- Self-hosted ntfy is deferred.

## Consequences

- Every automated job uses one notification interface.
- External heartbeat monitoring detects total system outages.
- Notification credentials remain centrally managed.

## Validation

- Test notifications reach the configured ntfy.sh topic.
- Missed healthchecks.io heartbeats generate alerts.
- Jobs invoke `notify.sh` instead of directly calling notification services.
