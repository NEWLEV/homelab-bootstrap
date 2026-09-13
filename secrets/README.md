# Aisha Encrypted Secrets

This directory stores only encrypted appliance-secret bundles and documentation.

Allowed in Git:

- `README.md`
- files ending in `.enc.yaml`

Never commit:

- age private keys
- plaintext credentials
- decrypted YAML files
- `.env` files
- API tokens
- backup passwords

The age private key is escrowed off-device in:

1. The user's password manager.
2. An encrypted offline USB stored separately from Aisha.

During disaster recovery, restore the age private key before running the
secret-restoration phase.

Host-specific bundles can be restored by setting `AISHA_SECRETS_BUNDLE`:

```bash
export SOPS_AGE_KEY_FILE=/srv/data/services/age/aisha-macmini.agekey
export AISHA_SECRETS_BUNDLE=secrets/aisha-macmini.enc.yaml
scripts/secrets-restore --check
```

Do not store the Age private key in Git. The corresponding public Age recipient
is safe to keep in `.sops.yaml`.
