# Updating Bootstrap Phases

The installer executes bootstrap phases defined in the bootstrap manifest rather than discovering scripts automatically.

## Bootstrap Manifest

The bootstrap manifest is located at:

```text
configs/bootstrap.json
```

Each enabled entry describes a single bootstrap phase.

Example:

```json
{
  "id": "docker",
  "script": "scripts/bootstrap.d/05-docker.sh",
  "description": "Docker and container runtime",
  "enabled": true
}
```

### Manifest fields

| Field | Description |
|------|-------------|
| `id` | Unique identifier displayed by the installer and logs. |
| `script` | Repository-relative path to the bootstrap script. |
| `description` | Human-readable description displayed during execution. |
| `enabled` | Whether the phase should be executed. Omit or set to `true` to enable the phase. Set to `false` to disable it. |

## Bootstrap Scripts

Bootstrap scripts are stored in:

```text
scripts/bootstrap.d/
```

Scripts should:

- be idempotent and safe to run multiple times
- exit with a non-zero status on failure
- contain valid Bash syntax
- perform one well-defined task
- avoid hardware-specific assumptions unless the script or phase is explicitly
  scoped to a hardware profile

## Supported Platforms

The bootstrap installer currently targets Debian-family Linux hosts. The
supported Debian package architectures are:

- `amd64`
- `arm64`

The live Aisha appliance is the Raspberry Pi 5 reference deployment, but
repository code should not require Raspberry Pi hardware unless it is working
on hardware telemetry, storage recovery, or another explicitly Pi-specific
feature.

Runtime paths under `/srv/data` remain the default durable-data layout. New
hosts may use the same path for repeatability, or override documented Compose
variables such as `TAILNET_BIND_IP`, `TRAEFIK_LAN_IP`, and
`HOMELAB_HOSTNAME` where host-specific addressing differs.

## Adding a New Bootstrap Phase

1. Create a new script in `scripts/bootstrap.d/`.
2. Make the script executable.

   ```bash
   chmod +x scripts/bootstrap.d/<script>.sh
   ```

3. Add a corresponding entry to `configs/bootstrap.json`.
4. Validate the installer.

   ```bash
   ./install.sh --list
   ./install.sh --dry-run
   ```

5. Run the validation suite.

   ```bash
   bash -n install.sh
   shellcheck install.sh scripts/bootstrap.d/*.sh
   ./tests/bootstrap-manifest.sh
   ```

6. Commit the changes only after all validation checks pass.

## Execution Order

Bootstrap phases are executed in the order they appear in `configs/bootstrap.json`.

The installer validates each enabled phase before execution, including:

- valid manifest syntax
- supported manifest schema
- required fields (`id`, `script`, and `description`)
- repository-relative script paths
- script existence
- non-empty scripts
- readable scripts
- successful Bash syntax validation

If any validation fails, the installer stops before executing any bootstrap phases.
