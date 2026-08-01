# ADR 0002: Secrets Escrow

- Status: Accepted
- Date: 2026-08-01

## Context

Aisha recovery depends on access to encrypted credentials and the key required to decrypt them. Keeping the only decryption key on Aisha would make recovery impossible after device loss or storage failure.

## Decision

- Repository-managed secrets will be encrypted with SOPS and age.
- The age private key will never be committed to Git.
- The key and recovery credential bundle will be escrowed in:
  - the user's password manager;
  - an encrypted offline USB stored separately from Aisha.
- The USB and password-manager records must identify the repository and include recovery instructions.
- Recovery documentation will require restoring the age key before the secrets-decryption phase.
- Real secrets will live in a gitignored `secrets/` directory.

## Consequences

- Recovery remains possible after complete device loss.
- Both escrow copies must be maintained and tested.
- Losing both escrow copies makes the encrypted secrets unrecoverable.
- Key rotation and USB refresh procedures must be documented.

## Validation

- A recovery test can restore the age key from an escrow copy.
- SOPS can decrypt the credential bundle on a fresh system.
- No private key or plaintext secret appears in Git.
