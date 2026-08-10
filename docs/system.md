# Aisha System Baseline

Inventory ID: `aisha-20260809`

Observed: 2026-08-09

Authority: `origin/main` at `b4d8517`

## Machine

Aisha is a bare-metal Raspberry Pi 5 with four Cortex-A76 cores, 15 GiB RAM,
and two 1 TB SK hynix NVMe drives. It runs Debian 13.6 on a Raspberry Pi
kernel. The root and data filesystems are ext4 and are not encrypted.

Thermals were healthy at 44.4°C with no throttling. Storage utilization was
3% on `/` and 1% on `/srv/data`.

## Runtime

The principal runtimes are OpenClaw 2026.7.1-2, Node.js 24.18.0, Python
3.13.5, Docker 29.7.1, and Git 2.47.3. Ten Docker containers were running at
inventory time. Several host services and manually launched processes are not
yet represented by repository state; see `drift-map.json`.

## Network posture

The host has Ethernet, Wi-Fi, and Tailscale interfaces, plus globally routed
IPv6. SSH and Traefik are expected to be the only broadly bound entry points.
Administrative interfaces are declared tailnet-only, while OpenClaw is
reachable through the secure Tailscale Serve Control UI and through the
same-origin Aisha chat gateway. UFW is active with deny-by-default IPv4 and
IPv6 input, but Docker forwarding currently precedes UFW; the repository
policy therefore adds an explicit `DOCKER-USER` chain.

The currently preferred OpenClaw posture is loopback-only gateway transport
with Tailscale Serve publishing `https://aisha.tail4553c9.ts.net/openclaw/`
for the stock Control UI. The same appliance also serves the Aisha chat
surface at `https://aisha.tail4553c9.ts.net/aisha/` for the Homepage
launcher. Repository state should keep the gateway on loopback so the browser
has a secure context and the launcher can remain same-origin.

The current live cutover verifies the secure tailnet URL and the Aisha chat
surface; the Homepage dashboard now also carries working shortcuts to Kuma,
File Browser, Portainer, Netdata, and Pironman5 Max, while Mission Control
remains explicitly marked coming soon. Any future native-gateway retirement
work should be tracked as a separate task rather than described as the active
state.

## Backup posture

The latest local and off-site encrypted Restic backup checks completed without
errors. Local restore scripting exists, but neither a mission-documented local
restore nor an off-site scratch restore has yet proven recovery.

## Reproducibility status

This machine is not yet reproducible from `main`. The drift map is the
authoritative backlog for reconciliation. A component becomes reproducible
only after its declaration, bootstrap/application path, validation,
monitoring, backup/restore behavior, and rollback are represented together.

## Knowledge indexing state

Local RAG now uses the clean, detached worktree at
`/srv/data/git/homelab-bootstrap-index`, pinned to reviewed merge commit
`0518e517c9080ed9d5d30a899d82a07104d15bfd` and mounted read-only.

The verified rebuild completed on 2026-08-10 with 96 indexed files and 132
chunks. Index integrity reported zero invalid records, and both
`docs/roadmap.md` and `docs/system-profile.json` were present in Chroma. The
pre-change Chroma snapshot remains at
`/srv/data/scratch/local-rag-chroma-pre-step0c-20260809` pending a separately
approved cleanup decision.
