# Infrastructure Manifest Schema

The infrastructure bootstrap manifest is the repo-backed source of truth for Phase 2.

## Top-Level Fields

- `name`: required string identifying the manifest.
- `services`: required non-empty list of service declarations.
- `volumes`: required list of named persistent volumes.
- `networks`: required list of named networks.

## Service Declaration Fields

Each service declaration supports:

- `name`: required unique service name.
- `image`: required container image.
- `depends_on`: optional list of upstream service names.
- `volumes`: optional list of volume names.
- `networks`: optional list of network names.
- `ports`: optional list of port mappings in Compose syntax.
- `environment`: optional string-to-string mapping.
- `healthcheck`: optional healthcheck URL or command description.

## Validation Rules

- service names must be unique
- dependencies must reference declared services
- service volume references must match declared volumes
- service network references must match declared networks
- all string values must be non-empty
- service lists and top-level lists must be valid YAML arrays

## Current Repository Manifest

The checked-in manifest lives at:

- [`bootstrap/infrastructure.yaml`](/C:/Users/ZBook/Documents/Aisha/bootstrap/infrastructure.yaml)

It defines the initial Phase 2 stack:

- reverse proxy
- monitoring
- backups
- shared volumes
- internal and edge networks
- explicit monitoring, backup, exposure, and readiness hooks
