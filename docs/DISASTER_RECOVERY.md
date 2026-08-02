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

---

# Recovery checklist

☐ secrets restored

☐ restic verified

☐ compose healthy

☐ validate.sh passes

☐ backups working

☐ notifications working

☐ documentation updated
