# Runtime Secrets

## Purpose

Sensitive runtime configuration is encrypted using SOPS and Age.

No plaintext secrets are committed to the repository.

---

# Recovery media

The recovery USB contains:

- AGE identity
- encrypted recovery material

The recovery media is only mounted during secret restoration.

---

# Restoring secrets

Mount the recovery USB.

```bash
sudo cryptsetup open /dev/sda1 aisha-recovery

sudo mount \
    /dev/mapper/aisha-recovery \
    /mnt/aisha-recovery
```

Set:

```bash
export SOPS_AGE_KEY_FILE=/mnt/aisha-recovery/age/aisha.agekey
```

Restore:

```bash
./install.sh --restore-secrets
```

---

# After restoration

Always remove recovery media.

```bash
sync

sudo umount /mnt/aisha-recovery

sudo cryptsetup close aisha-recovery

unset SOPS_AGE_KEY_FILE
```

---

# Security rules

- Never commit decrypted secrets.
- Never leave recovery media mounted.
- Never export AGE keys permanently.
- Remove recovery media immediately after use.
