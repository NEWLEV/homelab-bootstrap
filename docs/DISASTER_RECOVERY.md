# Disaster Recovery

## Goal

Rebuild the Aisha appliance from bare hardware.

Expected recovery time:
- Restore secrets: ~2 minutes
- Bootstrap: ~15 minutes
- Restore backups: depends on repository size

---

# Required items

- Raspberry Pi 5
- Boot SSD
- Data SSD
- Recovery USB
- GitHub repository
- Internet connection

---

# Recovery USB

Contents

- LUKS encrypted partition
- age identity
- recovery notes

Unlock

sudo cryptsetup open /dev/sdX1 aisha-recovery

mount

sudo mount /dev/mapper/aisha-recovery /mnt/aisha-recovery

export SOPS_AGE_KEY_FILE=/mnt/aisha-recovery/age/aisha.agekey

---

# Clone repository

git clone ...

---

# Restore secrets

./install.sh --restore-secrets

Verify

scripts/secrets-restore --check

---

# Bootstrap

./install.sh --apply

---

# Restore backups

scripts/restore-test

restic snapshots

restic restore ...

---

# Validate appliance

scripts/validate.sh

security/firewall.sh --dry-run

sudo security/firewall.sh --apply

sudo security/firewall.sh --verify

Expected result

PASS

---

# Bring services online

docker compose ...

Verify

homepage

traefik

OpenClaw

Local RAG

Confirm that the Aisha container has no host-published gateway port, the
native OpenClaw gateway binds only to loopback, administrative containers bind
only to the Tailscale address, and Traefik is the sole owner of LAN 80/443.
All persistent service paths remain covered by `/srv/data/services` in the
local and off-site Restic jobs; this network-only change adds no new state.

Verify the two intentionally separate OpenClaw runtimes and their ingress:

```bash
scripts/consolidate-openclaw --verify
```

Do not route `/openclaw/` to the Aisha container. The native gateway owns that
path, while the repo-managed container owns `/aisha/`.

---

# Recovery checklist

☐ secrets restored

☐ restic verified

☐ compose healthy

☐ validate.sh passes

☐ backups working

☐ notifications working

☐ documentation updated
