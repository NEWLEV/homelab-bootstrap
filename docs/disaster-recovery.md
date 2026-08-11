# Aisha Disaster Recovery Guide

## Purpose

This document describes the complete recovery procedure for rebuilding an Aisha system after hardware failure, operating system corruption, storage replacement, or accidental data loss.

The objective is to restore a fully functional system using:

- Git repository
- Bootstrap installer
- Repository-managed configuration
- Encrypted runtime secrets
- Recovery media

The recovery process is designed to be deterministic, repeatable, and fully documented.

Canonical backup and restore reference

```text
docs/backup-restore.md
```

---

# Recovery objectives

Recovery is complete when:

- The operating system boots successfully.
- `/srv/data` is mounted.
- The repository has been cloned.
- The bootstrap installer completes successfully.
- Runtime secrets have been restored.
- Required services are operational.
- Scheduled backups are functioning.
- The repository is clean.

---

# Recovery materials

The following items are required.

## Hardware

- Raspberry Pi 5
- NVMe system drive
- Recovery USB

## Software

- Raspberry Pi OS
- Git
- Internet connectivity

## Credentials

- GitHub access
- Sudo privileges
- Recovery USB passphrase

---

# Recovery procedure

## Step 1 - Install Raspberry Pi OS

Install Raspberry Pi OS onto the system drive.

After installation:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install git
```

Reboot if required.

---

## Step 2 - Clone the repository

Clone the homelab repository.

```bash
cd /srv/data/git
git clone https://github.com/NEWLEV/homelab-bootstrap.git
cd homelab-bootstrap
```

Switch to the desired release if necessary.

---

## Step 3 - Validate the installer

Confirm the installer can discover bootstrap phases.

```bash
./install.sh --list
```

Expected output:

- system
- storage
- docker

---

## Step 4 - Perform a dry run

Validate the installation without making changes.

```bash
./install.sh --dry-run
```

Expected results:

- manifest loads successfully
- bootstrap phases discovered
- no validation failures

---

## Step 5 - Execute the bootstrap

Run the installer.

```bash
./install.sh --apply
```

The installer will:

- configure the operating system
- configure storage
- install Docker
- execute all enabled bootstrap phases

Review the output for any reboot recommendations.

---

## Step 6 - Mount the recovery USB

Unlock the encrypted recovery media.

```bash
sudo cryptsetup open /dev/sda1 aisha-recovery

sudo mkdir -p /mnt/aisha-recovery

sudo mount /dev/mapper/aisha-recovery \
    /mnt/aisha-recovery
```

Verify:

```bash
findmnt /mnt/aisha-recovery
```

---

## Step 7 - Restore runtime secrets

Provide the AGE identity.

```bash
export SOPS_AGE_KEY_FILE=/mnt/aisha-recovery/age/aisha.agekey
```

Verify:

```bash
test -r "$SOPS_AGE_KEY_FILE"
```

Restore secrets.

```bash
./install.sh --restore-secrets
```

Expected output:

- Runtime secrets restored
- All secrets current
- No missing files

---

## Step 8 - Remove recovery media

After secrets have been restored:

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

- recovery media unmounted
- LUKS container inactive
- AGE key removed from environment

---

## Step 9 - Start services

Start configured services.

Example:

```bash
docker compose up -d
```

or

```bash
systemctl start <service>
```

depending on the component.

---

## Step 10 - Verify the system

Run:

```bash
git status

./install.sh --dry-run

docker compose ls

systemctl --failed
```

Expected results:

- clean repository
- no failed services
- installer passes validation
- containers running

---

# Recovery checklist

- [ ] Operating system installed
- [ ] Repository cloned
- [ ] Bootstrap completed
- [ ] Runtime secrets restored
- [ ] Recovery media removed
- [ ] Services running
- [ ] Backups verified
- [ ] Repository clean

---

# Troubleshooting

## Installer fails

Review:

```
/srv/data/logs/bootstrap/install-*.log
```

Correct the reported issue and rerun:

```bash
./install.sh --apply
```

---

## Secret restoration fails

Verify:

```bash
echo "$SOPS_AGE_KEY_FILE"

test -r "$SOPS_AGE_KEY_FILE"
```

Confirm the recovery USB is mounted.

---

## Repository cannot be cloned

Verify:

- Internet connectivity
- GitHub access
- Repository URL

---

## Bootstrap validation fails

Run:

```bash
./install.sh --list

./install.sh --dry-run
```

Resolve any reported validation errors before applying the installer.

---

# Post-recovery

After recovery:

- Verify backups.
- Commit documentation updates.
- Push repository changes.
- Store the recovery USB securely.
