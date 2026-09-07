# Supported Platforms

This repository is intended to be usable from GitHub on more than the live
Aisha Raspberry Pi.

## Reference Deployment

The current production appliance is:

- Hostname: `aisha`
- Hardware: Raspberry Pi 5
- Operating system: Raspberry Pi OS Lite 64-bit
- Architecture: `arm64`
- Durable data root: `/srv/data`

Files such as `docs/system.md`, `docs/system-profile.json`, and
`docs/drift-map.json` may describe that live reference host directly.

## Portable Bootstrap Target

The bootstrap scripts currently support Debian-family Linux systems with:

- `amd64`
- `arm64`

The project should not introduce new Raspberry Pi-only checks in shared
bootstrap code. Hardware-specific behavior belongs in clearly named scripts,
docs, or service profiles.

## System Recommendations

Run the read-only recommendation command before applying a new host:

```bash
./install.sh --recommend
```

The command inspects the current system and suggests platform profile,
storage readiness, host-specific Compose values, and a local Ollama model set.

## Host-Specific Configuration

The checked-in Compose files use Aisha defaults, but common host values are
configurable:

| Variable | Purpose | Aisha default |
|----------|---------|---------------|
| `TAILNET_BIND_IP` | Tailnet interface/IP used for directly bound service ports | `100.106.201.14` |
| `TRAEFIK_LAN_IP` | LAN IP used for Traefik HTTPS exposure | `192.168.1.97` |
| `TAILSCALE_SERVE_HOST` | Tailnet HTTPS hostname used by ingress scripts | `aisha.tail4553c9.ts.net` |
| `HOMELAB_HOSTNAME` | Hostname advertised to services such as Netdata | `aisha` |
| `AISHA_KNOWLEDGE_SOURCE` | Local RAG indexed source checkout | `/srv/data/git/homelab-bootstrap-index` |

Use environment variables or a local Compose env file for host-specific
overrides. Do not commit private host addresses, secrets, or one-off runtime
state as a portability fix.

Start from `configs/host.env.example` when preparing a new host profile.

## MacBooks

MacBooks are supported as development and control machines. They are the right
place to edit the repository, review GitHub changes, run portable checks, and
control remote Linux hosts over SSH.

The bootstrap installer does not apply host changes directly on macOS. Use
`./install.sh --recommend` for local guidance, then apply bootstrap phases from
a Debian-family Linux host, Linux VM, or the target homelab machine.
