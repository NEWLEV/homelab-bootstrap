# Mission Control Service

Mission Control is the operational dashboard for agent activity, approvals, vitals, and digest replay.

## Start On Aisha

1. Build or run the container image from the repo root.
2. Bind the service to the internal network only.
3. Mount the `mission-control-data` volume at `/data/mission-control`.
4. Provide the shared `MISSION_CONTROL_TOKEN` secret.

## Safe Operation

- Mission Control is read-first and does not execute actions itself.
- Approvals are resolved only by record updates and emitted events.
- The SQLite database lives on the persistent `mission-control-data` volume.

## Related Files

- `Dockerfile` builds the Mission Control runtime image.
- `scripts/run-mission-control.sh` launches the service manually from the repo root.
- `scripts/install-mission-control-service.sh` installs the user-level systemd unit.
- `systemd/aisha-mission-control.service` is the user-level systemd unit template.
