# ADR 0003: Boot Medium

- Status: Accepted
- Date: 2026-08-01

## Context

Storage health monitoring differs between NVMe and SD-card installations. Aisha currently uses separate NVMe devices for the operating system and persistent data.

## Decision

- Aisha boots from NVMe.
- Persistent data resides on a second NVMe device mounted at `/srv/data`.
- SMART and NVMe health monitoring are supported.
- Bootstrap storage scripts validate the existing layout and never automatically partition, format, or mount data-bearing disks.
- Future SD-card deployments are treated as a separate hardware profile with SD-specific health checks.

## Consequences

- SMART monitoring is part of the standard platform.
- Storage bootstrap remains non-destructive.
- Documentation will assume the dual-NVMe layout.

## Validation

- `/` and `/srv/data` are on separate NVMe devices.
- SMART/NVMe monitoring is operational.
- Storage validation completes without modifying disks.
