# Aisha Homelab Bootstrap

Aisha is an infrastructure-as-code project for provisioning, operating, and maintaining a reproducible Linux homelab. The live reference appliance is a Raspberry Pi 5, but the GitHub repository is intended to work on supported Debian-family Linux hosts, including `amd64` and `arm64` systems. MacBooks are supported as development and control machines.

The repository contains:

- Bootstrap automation
- Service definitions
- Infrastructure configuration
- Documentation
- Tests
- Continuous Integration

The project is designed around declarative configuration, repeatable automation, and documented operational procedures.

---

# Features

- Manifest-driven bootstrap installer
- Idempotent bootstrap phases
- Docker Compose infrastructure
- Local AI services
- Portable Debian-family Linux bootstrap with Aisha reference defaults
- Encrypted runtime secrets (SOPS + Age)
- Disaster recovery procedures
- Automated validation with GitHub Actions
- Regression testing
- Comprehensive operational documentation

---

# Repository Layout

```text
compose/                 Docker Compose definitions
configs/                 Repository configuration
docs/                    Documentation
monitoring/              Monitoring utilities
scripts/                 Operational scripts
scripts/bootstrap.d/     Bootstrap phases
security/                Security configuration
services/                Service implementations
tests/                   Regression tests
install.sh               Bootstrap installer
```

---

# Getting Started

Clone the repository.

```bash
git clone https://github.com/NEWLEV/homelab-bootstrap.git

cd homelab-bootstrap
```

Validate the installer.

```bash
./install.sh --list

./install.sh --recommend

./install.sh --dry-run
```

For a non-Aisha host, review `docs/platforms.md` and start from
`configs/host.env.example` before running Compose services. On a MacBook, use
`./install.sh --recommend` for guidance, then run `--apply` on a Linux target
or VM.

Apply the bootstrap.

```bash
./install.sh --apply
```

Restore runtime secrets.

```bash
export SOPS_AGE_KEY_FILE=/mnt/aisha-recovery/age/aisha.agekey

./install.sh --restore-secrets
```

---

# Documentation

| Document | Description |
|----------|-------------|
| `docs/architecture.md` | System architecture |
| `docs/bootstrap.md` | Bootstrap process |
| `docs/platforms.md` | Supported host platforms and portability rules |
| `docs/storage.md` | Storage layout |
| `docs/network.md` | Network architecture |
| `docs/services.md` | Managed services |
| `docs/secrets.md` | Secret management |
| `docs/disaster-recovery.md` | Disaster recovery |
| `docs/developer-guide.md` | Development workflow |
| `docs/release-process.md` | Release workflow |
| `docs/roadmap.md` | Platform scope and delivery status |
| `SECURITY.md` | Security policy and public repository rules |
| `docs/system.md` | Current machine profile and operational posture |
| `docs/system-profile.json` | Structured system inventory baseline |
| `docs/drift-map.json` | Live-to-repository reconciliation map |
| `docs/mission-events.jsonl` | Mission Control-compatible action trail |
| `docs/mission-approvals.jsonl` | Operator approval trail |
| `docs/step0c-application-20260810.json` | Step 0C live application evidence |

---

# Development

Before opening a pull request, validate the repository.

```bash
bash -n install.sh

shellcheck install.sh

./tests/bootstrap-manifest.sh

bash tests/platform-portability.sh

./install.sh --dry-run

./scripts/health
```

Run any additional tests affected by your changes.

`./scripts/healthcheck` is kept as an alias for `./scripts/health`.

---

# Continuous Integration

Every pull request is validated automatically.

Current checks include:

- Shell validation
- Bootstrap manifest validation
- Configuration validation
- Docker Compose validation
- Local RAG tests

Changes should not be merged until all required checks pass.

---

# Design Principles

The project is built around the following principles:

- Infrastructure as Code
- Declarative configuration
- Idempotent automation
- Secure secret management
- Automated validation
- Repeatable recovery
- Comprehensive documentation
