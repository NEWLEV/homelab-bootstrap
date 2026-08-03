# Architecture

## Repository layout

```
configs/
docs/
scripts/
scripts/bootstrap.d/
services/
tests/
install.sh
```

---

## Bootstrap workflow

```
install.sh
        │
        ▼
Preflight validation
        │
        ▼
Load bootstrap manifest
        │
        ▼
Validate manifest
        │
        ▼
Discover enabled phases
        │
        ▼
Execute phases in order
        │
        ▼
Restore runtime secrets (optional)
        │
        ▼
Summary
```

---

## Design principles

- Declarative bootstrap manifest
- Idempotent bootstrap scripts
- Repository-managed configuration
- Encrypted runtime secrets
- Automated validation
- Continuous integration
