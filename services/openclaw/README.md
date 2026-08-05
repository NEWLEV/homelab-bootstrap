# OpenClaw Service Scaffold

This directory defines the first contract for the OpenClaw service foundation.

Current scope:
- document the intended runtime boundary
- keep the service wired to encrypted runtime secrets
- reserve durable state under /srv/data/services/openclaw
- avoid exposing the service outside the local host until authentication and tooling policies are finalized

Planned runtime pieces:
- gateway process / API container
- local RAG integration
- explicit environment file sourced from the secret restore workflow
- health check and startup wiring

Current runtime contract:
- `start.sh` validates the secrets file exists and prints the resolved runtime paths
- `healthcheck.sh` validates the mounted secret boundary and the runtime gateway contract
- `Dockerfile` builds a small image around those scripts
- Compose mounts durable state under `/srv/data/services/openclaw`

This directory intentionally starts as a scaffold, not the final implementation.
