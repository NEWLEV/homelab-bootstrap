# Storage

## Purpose

This document describes the storage architecture of the Aisha homelab, including the operating system, application data, recovery media, and backup strategy.

---

# Storage Overview

The system uses separate storage devices for operating system files, persistent application data, and disaster recovery.

| Device | Purpose |
|---------|---------|
| System NVMe | Raspberry Pi OS and system software |
| Data NVMe | Persistent application data (`/srv/data`) |
| Recovery USB | Encrypted recovery media containing the Age identity and recovery assets |

---

# Filesystem Layout

```
/
├── boot
├── etc
├── home
├── srv
│   └── data
│       ├── git
│       ├── logs
│       ├── services
│       └── backups
```

Persistent data resides under:

```
/srv/data
```

The operating system should contain only operating-system components and user configuration.

---

# System Drive

Purpose:

- Raspberry Pi OS
- installed packages
- system configuration
- bootloader

Verify:

```bash
lsblk -f
```

Example:

```
nvme0n1
├── bootfs
└── rootfs
```

---

# Data Drive

Purpose:

- Git repositories
- Docker data
- application configuration
- installer logs
- service data
- backups

Mounted at:

```
/srv/data
```

Verify:

```bash
findmnt /srv/data
```

Expected result:

```
/srv/data
```

---

# Repository Location

The homelab repository resides at:

```text
/srv/data/git/homelab-bootstrap
```

Verify:

```bash
git status
```

The working tree should normally be clean.

---

# Installer Logs

Bootstrap logs are stored in:

```text
/srv/data/logs/bootstrap/
```

Example:

```bash
ls -lh /srv/data/logs/bootstrap
```

---

# Recovery Media

The recovery USB stores material required for disaster recovery.

Contents include:

- Age identity
- encrypted recovery assets

The recovery media is encrypted using LUKS.

Normal state:

- disconnected or securely stored
- not mounted
- LUKS container closed

Verify:

```bash
sudo cryptsetup status aisha-recovery

findmnt /mnt/aisha-recovery
```

Expected output:

```
/dev/mapper/aisha-recovery is inactive.
```

---

# Mounting Recovery Media

Unlock:

```bash
sudo cryptsetup open /dev/sda1 aisha-recovery
```

Mount:

```bash
sudo mkdir -p /mnt/aisha-recovery

sudo mount \
    /dev/mapper/aisha-recovery \
    /mnt/aisha-recovery
```

Verify:

```bash
findmnt /mnt/aisha-recovery
```

---

# Unmounting Recovery Media

After secret restoration:

```bash
sync

sudo umount /mnt/aisha-recovery

sudo cryptsetup close aisha-recovery

unset SOPS_AGE_KEY_FILE
```

Verify:

```bash
findmnt /mnt/aisha-recovery

sudo cryptsetup status aisha-recovery
```

Expected results:

- recovery filesystem unmounted
- encrypted container closed
- no exported Age key

---

# Backup Storage

Backups are written using Restic.

Repository configuration is documented separately.

Verify:

```bash
restic snapshots
```

---

# Storage Health

Monitor storage usage with:

```bash
df -h

lsblk -f

findmnt
```

Check filesystem usage:

```bash
du -sh /srv/data/*
```

---

# Troubleshooting

## /srv/data is not mounted

Verify:

```bash
findmnt /srv/data
```

The installer will refuse to continue until the mount is available.

---

## Recovery USB cannot be opened

Verify:

- correct USB device
- correct LUKS passphrase

Inspect:

```bash
lsblk -f

sudo cryptsetup status aisha-recovery
```

---

## Repository missing

Clone the repository:

```bash
cd /srv/data/git

git clone https://github.com/NEWLEV/homelab-bootstrap.git
```

---

# Design Principles

- Separate operating system from persistent data.
- Keep all application data under `/srv/data`.
- Store recovery material on encrypted removable media.
- Never store plaintext secrets on persistent disks.
- Keep the recovery USB disconnected except during recovery operations.
