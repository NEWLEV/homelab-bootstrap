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
