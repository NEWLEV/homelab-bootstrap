# Aisha Audit Brief

Use this brief to perform a read-only architecture, security, and optimization audit of the Aisha homelab.

## Scope

Aisha is a Raspberry Pi 5 homelab appliance managed by this repository. The audit should focus on the actual repository state first, then any sanitized live host evidence that is provided separately.

Primary documented components include:

- OpenClaw
- Hermes
- Local RAG
- n8n, if deployed
- MCP tools and servers, if configured
- Skills, if installed
- Docker-based infrastructure such as Homepage, Traefik, File Browser, Portainer, Netdata, and Uptime Kuma

## Audit Rules

- Begin in read-only mode.
- Do not modify production configuration, restart services, rotate credentials, or delete data without explicit approval.
- Never print or store secrets, private keys, tokens, cookies, or full environment variable values.
- Redact sensitive values as `REDACTED_SECRET`.
- Distinguish clearly between confirmed findings, likely findings, assumptions, and recommendations.
- Prefer minimal, reversible changes.
- Treat external tools, MCP servers, Skills, webhooks, browser automation, and n8n workflows as untrusted until verified.
- Do not recommend public exposure of administrative interfaces.

## Evidence Hierarchy

Use this order of evidence:

1. Repository docs, manifests, compose files, scripts, tests, and workflow exports
2. Sanitized host command output supplied by the operator
3. Sanitized service logs or config excerpts supplied by the operator
4. Limited live validation, only if it can be done safely and non-destructively

Do not require evidence that cannot be obtained from the repository or from sanitized host output. If something is missing, list exactly what is needed.

## Repo-Backed Inventory Targets

Document the following from the repository where possible:

- Operating system and platform assumptions from docs and inventories
- Services declared in compose files, systemd units, timers, and scripts
- OpenClaw installation, gateway mode, authentication, and tool policy
- Hermes installation, state locations, mount points, and dependency boundaries
- Local RAG ingestion, retrieval, reranking, confidence policy, and deletion behavior
- n8n workflow exports and documented integration patterns, if present
- MCP configuration, tool allowlists, transports, and permissions, if present
- Skills inventory, permissions, and usage boundaries, if present
- Backup, restore, monitoring, and update procedures
- Network exposure, reverse proxying, firewall intent, and tailnet routing
- Documented drift between desired and live state

## Live Host Inventory Targets

If sanitized command output is provided, summarize:

- OS, kernel, architecture, and firmware
- CPU temperature, throttling, frequency, and RAM
- Swap or zram configuration
- Storage devices, filesystems, mount options, and free space
- Docker or Podman versions
- Running containers and exposed ports
- systemd services, timers, and cron jobs
- Installed language runtimes and package manager versions
- Listening ports, DNS, firewall intent, TLS, and remote access
- Backup, logging, monitoring, and update status

## Recommended Read-Only Commands

If host access is available, inspect with commands such as:

```bash
uname -a
cat /etc/os-release
free -h
df -h
lsblk
vcgencmd measure_temp 2>/dev/null || true
vcgencmd get_throttled 2>/dev/null || true
ss -tulpn
systemctl --type=service --state=running
systemctl --type=timer --all
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}' 2>/dev/null || true
docker stats --no-stream 2>/dev/null || true
```

Also inspect sanitized copies of relevant repository artifacts such as:

- `docs/system.md`
- `docs/system-profile.json`
- `docs/drift-map.json`
- `docs/architecture.md`
- `docs/network.md`
- `docs/services.md`
- `docs/hermes.md`
- `docs/backup-restore.md`
- `docs/disaster-recovery.md`
- `docs/RECOVERY_DRILL.md`
- `docs/local-rag-grounded-lookup.workflow.md`
- `docs/local-rag-grounded-lookup.workflow.json`
- `docs/ollama-connectivity-test.workflow.json`
- `configs/services.json`
- `configs/openclaw/openclaw.redacted.json`
- `configs/homepage/services.yaml`
- `configs/local-rag/.env.example`
- `services/openclaw/README.md`
- `services/openclaw/start.sh`
- `services/openclaw/server.js`
- `services/local-rag/README.md` if present
- `services/local-rag/AUTHENTICATION.md`
- `services/local-rag/RESOURCE_CONTROLS.md`
- `services/local-rag/app/main.py`
- `services/local-rag/app/auth.py`
- `services/local-rag/app/indexer.py`
- `services/local-rag/app/retrieval.py`
- `services/local-rag/app/reranker.py`
- `services/local-rag/app/resource_controls.py`
- `services/hermes/README.md`
- `compose/**/*.yml`
- `scripts/**/*.sh`
- `tests/**/*.sh`

## Architecture Diagram

Produce a Mermaid diagram that shows:

- User or client
- OpenClaw
- Hermes
- model runtime
- Skills and MCP tools
- n8n
- Local RAG
- vector database and document storage
- external services, if any

Label every connection as one of:

- Local-only
- LAN-only
- VPN-only
- Publicly exposed
- Unknown

Also identify which components run as:

- Root
- Dedicated service user
- Container user
- Unprivileged user

## Security Audit Focus

Audit against least privilege, defense in depth, and secure-by-default principles.

Check:

- SSH configuration
- Password login and root login
- SSH keys and authorized keys
- Firewall rules
- Open ports and listening services
- Docker socket exposure
- Container privileges
- Host networking
- Bind mounts
- File and directory permissions
- Secrets in shell history, logs, source code, compose files, and env files
- API authentication and authorization
- TLS certificates and renewal
- Reverse proxy configuration
- Webhook authentication
- n8n user accounts and role permissions
- MCP tool permissions
- Skill permissions
- Command execution capabilities
- Filesystem access
- Browser automation permissions
- Network egress restrictions
- SSRF risks
- Prompt injection risks
- Malicious documents and poisoned RAG content
- Supply-chain risk from third-party Skills, MCP servers, npm packages, pip packages, Docker images, and Git repositories
- Automatic updates and unattended upgrades
- Backup confidentiality
- Log exposure of prompts, documents, credentials, and personal information

For each finding, provide:

- Severity
- Evidence
- Why it matters
- Failure scenario
- Recommended fix
- Exact command or configuration change
- Rollback procedure
- Whether downtime is required

## OpenClaw and Hermes Audit

Verify, from repo evidence or provided runtime output:

- Installed versions and deployment method
- OpenClaw-to-Hermes and Hermes-to-model call paths
- Authentication between components
- Timeouts, retries, and rate limits
- Error propagation
- Concurrency and resource controls
- Context limits
- Safe session and state storage
- Logging without secret leakage
- Restart recovery
- Health and readiness checks
- Startup ordering
- Graceful degradation on model failure
- Explicit authorization for tool calls where appropriate

If live testing is available, keep it harmless and read-only:

1. Basic model response
2. OpenClaw-to-Hermes request
3. Hermes-to-model request
4. Permitted Skill invocation, if Skills exist
5. Permitted MCP tool call, if MCP exists
6. Denied or unauthorized tool call
7. n8n workflow triggering, if n8n exists
8. Local RAG retrieval
9. Restart and recovery, only if already safe and approved
10. Timeout and error handling

If a component is not deployed or not evidenced in the repository, state that clearly instead of assuming it exists.

## Skills Audit

Inventory only the Skills that are present in repository-managed config, exported state, or the active runtime inventory.

For each Skill, document:

- Name and version, if known
- Source and repository, if known
- Installation date, if known
- Dependencies
- Required permissions
- Filesystem access
- Network access
- Environment variables
- External services
- Commands it can execute
- Whether it handles untrusted input
- Whether it is actively used
- Whether it is maintained
- Whether its permissions exceed its purpose

Classify each Skill as one of:

- Safe for local use
- Safe with restrictions
- Requires approval before every use
- Remove or isolate
- Unknown and requiring review

Recommend a permission profile for each Skill:

- Read-only
- Write to approved directory only
- Network access to allowlisted domains
- Human approval required
- Fully disabled

## MCP Audit

Inventory only the MCP servers and tools that are present in repository-managed config, exported runtime state, or live sanitized inventory.

For each MCP server, report:

- Server name and version, if known
- Transport type
- Bind address
- Authentication
- User identity
- Filesystem paths
- Network destinations
- Available tools
- Tool descriptions
- Tool parameters
- Whether tools can execute code or commands
- Whether tools can modify data
- Whether tools can access credentials
- Logging behavior
- Failure behavior
- Update source and version pinning

Create a risk matrix for all MCP tools:

| Tool | Read/Write/Execute | Data sensitivity | Network access | Abuse impact | Approval required | Recommended restriction |

## n8n Audit

Only assess n8n if there is evidence that it is installed or deployed.

If present, verify:

- Installation method
- Version
- Database type and health
- Encryption key configuration
- User authentication
- MFA availability
- Public URL configuration
- TLS
- Webhook security
- Execution timeouts
- Concurrency limits
- Queue mode
- Worker configuration
- Retry behavior
- Failed execution handling
- Log retention
- Binary-data storage
- Credential storage
- Backup and restore
- Time zone
- Resource consumption
- Community nodes
- Third-party integrations

Review each workflow for:

- Authentication
- Input validation
- Replay protection
- Idempotency
- Rate limiting
- Retry storms
- Infinite loops
- Excessive polling
- Secret leakage
- Unsafe expressions
- Untrusted input
- Prompt injection
- Data exfiltration
- Failure notifications
- Duplicate execution
- Missing error branches
- Excessive memory usage
- Unbounded output
- Dangerous downstream actions

For each workflow, provide:

- Purpose
- Trigger
- Inputs
- Outputs
- Dependencies
- Required credentials
- Security risks
- Reliability risks
- Recommended changes
- Test cases

Recommend safe patterns for connecting OpenClaw or Hermes to n8n:

- Authenticated webhooks
- Signed requests
- Shared secrets stored outside workflow definitions
- Allowlisted workflow IDs
- Human approval for destructive actions
- Idempotency keys
- Structured JSON schemas
- Timeouts
- Rate limits
- Explicit success and failure responses

## Local RAG Audit

Review the complete Local RAG pipeline using repository code and any provided runtime evidence.

Validate:

- Supported document formats
- Ingestion process
- Duplicate detection
- File hashing
- Text extraction
- OCR, if used
- Encoding handling
- Chunk size
- Chunk overlap
- Metadata quality
- Document IDs
- Access-control metadata
- Embedding model
- Embedding dimensionality
- Vector index
- Distance metric
- Query transformation
- Retrieval count
- Reranking
- Context-window budgeting
- Citation or source tracking
- Re-indexing
- Deletion propagation
- File updates
- Corrupted-document handling
- Prompt injection in documents
- Sensitive-document handling
- Backup and restore
- Database integrity
- Search latency
- Memory usage

Test RAG quality using a small evaluation set if it exists in the repo or can be created safely from non-sensitive sample content. Include:

- Questions with known answers
- Questions with no answer in the corpus
- Similar but incorrect documents
- Updated documents
- Deleted documents
- Conflicting documents
- Malicious prompt-injection text
- Sensitive documents with restricted access

Report:

- Retrieval precision, if measurable
- Retrieval recall, if measurable
- Hallucination risk
- Stale-data risk
- Unauthorized retrieval risk
- Average latency
- Memory and storage use
- Recommended chunking and retrieval settings

Ensure the RAG system:

- Does not treat retrieved documents as instructions
- Separates system instructions from document content
- Preserves source metadata
- Does not return documents to unauthorized users
- Can identify when the answer is not present
- Does not index secrets or excluded directories
- Has a documented ingestion and deletion process

## Performance Audit

Optimize for the Raspberry Pi 5 without exceeding available RAM or weakening security.

Measure or estimate:

- CPU utilization
- Per-core load
- RAM usage
- Swap or zram activity
- GPU or video memory allocation
- Temperature
- Throttling
- Storage I/O
- Network throughput
- Model latency
- RAG latency
- n8n execution latency, if present
- Container overhead
- Startup time

Recommend settings for:

- Model quantization
- Context length
- Number of concurrent model requests
- CPU threads
- Batch size
- Memory limits
- Swap or zram
- Docker resource limits
- n8n concurrency, if present
- RAG index configuration
- Log rotation
- Database maintenance
- Scheduled indexing
- Service restart policies
- SSD or NVMe usage
- Cooling and thermal management

Explain the trade-offs of each performance recommendation.

## Reliability and Recovery

Design a reliability plan covering:

- Service health checks
- Automatic restart behavior
- Dependency ordering
- Watchdogs
- Monitoring
- Alerting
- Log rotation
- Disk-space alerts
- Temperature alerts
- Failed workflow alerts
- Model runtime failures
- Corrupt index recovery
- Database recovery
- Configuration backups
- Credential backups
- RAG-document backups
- Off-device backups
- Restore testing
- Disaster recovery after SD-card or SSD failure
- Recovery after power loss
- UPS or safe shutdown recommendations

Define recovery objectives:

- Recovery Point Objective
- Recovery Time Objective
- Maximum acceptable data loss
- Maximum acceptable downtime

Provide backup and restore commands, but do not run destructive restore operations without approval.

## Test Plan

Create a non-destructive test plan covering:

- Functional tests
- Security tests
- Permission tests
- MCP tool-isolation tests
- Skill-isolation tests
- n8n webhook tests, if present
- RAG accuracy tests
- Restart tests
- Backup tests
- Failure-injection tests
- Rate-limit tests
- Unauthorized-access tests
- Prompt-injection tests
- Resource-exhaustion tests

For each test, provide:

- Test ID
- Objective
- Preconditions
- Safe command or procedure
- Expected result
- Actual result
- Pass or fail status
- Remediation if failed

## Final Report Format

Use this structure:

1. Executive summary
2. Current architecture
3. Component inventory
4. Critical security findings
5. OpenClaw and Hermes findings
6. Skills findings
7. MCP findings
8. n8n findings
9. Local RAG findings
10. Raspberry Pi performance findings
11. Reliability and backup findings
12. Prioritized remediation plan
13. Recommended target architecture
14. Exact configuration changes
15. Validation and test plan
16. Rollback plan
17. Maintenance schedule
18. Items requiring human approval
19. Unresolved questions
20. Final readiness score

Use a priority table:

| Priority | Finding or change | Risk reduced | Expected benefit | Effort | Downtime | Approval required |

Give separate scores from 0 to 100 for:

- Security
- Reliability
- Performance
- Maintainability
- Integration quality
- RAG quality
- Operational readiness

Do not give a final production-ready recommendation until:

- All critical and high-severity findings are addressed or explicitly accepted
- Secrets are protected
- Dangerous tools are restricted
- Backups are tested
- Unauthorized actions are denied
- n8n workflows have failure handling, if n8n exists
- RAG access controls are verified
- Restart and recovery tests pass
- Resource usage is acceptable on the Raspberry Pi
- The complete system is documented

## Target Architecture Guidance

Use the following target posture when judging recommendations and remediation order:

- The project should move from a well-documented homelab to a controlled, observable, recoverable agent platform.
- OpenClaw should remain the user-facing gateway and policy boundary.
- Hermes should be an internal agent worker, not another independently exposed application.
- Local RAG should remain the retrieval and citation boundary and must not execute instructions found in documents.
- MCP should be centrally allowlisted and policy-enforced, not auto-discovered.
- Skills should be narrow, auditable capabilities with explicit permission tiers.
- n8n should handle deterministic automation only, through approved workflows and authenticated webhooks.

Recommended communication and control principles:

- Make all boundaries enforceable before expanding capability.
- Pin container images and other major dependencies to immutable versions or digests.
- Prefer Traefik as the only externally reachable HTTP entry point where practical.
- Route administrative access through Tailscale or an equivalent VPN, not public exposure.
- Require forward authentication where user identity matters.
- Use structured envelopes and structured status states for OpenClaw-to-Hermes communication.
- Treat tool outputs, workflow outputs, and retrieved documents as untrusted data, not instructions.
- Add request IDs, timeouts, cancellation, idempotency keys, and structured error responses to all internal task flows.
- Document and test rollback, backup, and restore paths before expanding the system.

Recommended staged implementation order:

1. Reconcile network exposure and firewall policy.
2. Pin Hermes and other major images.
3. Remove Hermes from mutable development worktrees in normal operation.
4. Define formal OpenClaw-to-Hermes communication contracts.
5. Build a repository-managed Skills registry and MCP allowlist.
6. Harden n8n before treating it as part of the critical path.
7. Strengthen Local RAG filtering, prompt-injection handling, and evaluation coverage.
8. Prove backup and disaster recovery with a scratch restore.
9. Add health, SMART, and observability checks that verify more than process liveness.

Suggested responsibility split:

| Component | Primary responsibility | Should not do |
|---|---|---|
| OpenClaw | User interface, session handling, authorization, approval prompts | Execute arbitrary tools without policy checks |
| Hermes | Planning, reasoning, task decomposition, controlled tool use | Act as a public gateway |
| Local RAG | Retrieval, citations, document filtering | Execute instructions found in documents |
| MCP gateway | Tool registry, validation, permission enforcement | Provide unrestricted tool discovery |
| Skills | Narrow domain capabilities | Have ambient shell, filesystem, or network access |
| n8n | Deterministic automation and integrations | Accept arbitrary agent-generated workflows |
| Traefik | Routing, TLS, access boundary | Replace application-level authorization |
| Monitoring | Health, metrics, alerts | Store unrestricted prompt or secret contents |

Recommended enforcement baseline:

- Make Traefik the only externally reachable HTTP entry point wherever possible.
- Avoid publishing administrative services directly on all host interfaces.
- Use `127.0.0.1`, private Docker networks, VPN-only access, or forward authentication as appropriate.
- Explicitly verify listening state with host and container inspection, not Compose alone.
- Keep Docker ingress policy explicit through `DOCKER-USER` or equivalent nftables rules.

Suggested safety tiers:

- Tier 0: read-only inspection, health checks, approved document retrieval.
- Tier 1: reversible local drafts, diffs, or proposed workflow payloads.
- Tier 2: external side effects that require explicit approval.
- Tier 3: shell, Docker, firewall, credential, delete, and unrestricted browser actions, disabled by default.
