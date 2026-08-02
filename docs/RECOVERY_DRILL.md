# Aisha Recovery Drill

## Purpose

Validate recovery of the Aisha appliance from a fresh operating-system installation.

## Release target

Corrected Bootstrap Appliance release: `v1.6.1`

## Start conditions

- Fresh Raspberry Pi OS installation
- Root NVMe prepared
- Data NVMe mounted at `/srv/data`
- Recovery USB available
- GitHub access available
- Network and Tailscale access available
- Latest Restic backup available

## Timing

- Drill start:
- Operating system ready:
- Repository cloned:
- Recovery USB unlocked:
- Secrets restored:
- Bootstrap completed:
- Backup restored:
- Validation passed:
- Drill end:
- Total recovery time:

## Procedure

1. Install the operating system.
2. Configure networking and Tailscale SSH.
3. Mount `/srv/data`.
4. Clone the repository.
5. Unlock and mount the encrypted recovery USB.
6. Set `SOPS_AGE_KEY_FILE`.
7. Run `./install.sh --restore-secrets`.
8. Run `./install.sh --apply`.
9. Run `./install.sh --apply` a second time.
10. Restore persistent data from Restic.
11. Run `./scripts/validate.sh`.
12. Verify backups and scheduled timers.
13. Record manual steps, failures, and recovery duration.

## Acceptance results

- [ ] Secrets restore succeeded.
- [ ] First bootstrap run succeeded.
- [ ] Second bootstrap run made no unintended changes.
- [ ] Restic restore succeeded.
- [ ] `scripts/validate.sh` passed.
- [ ] Services survived reboot.
- [ ] Backup timers are enabled and active.
- [ ] Actual RTO recorded.
- [ ] Manual recovery steps documented.

## Issues found

## Remediation completed

## Final result

- Status: Pending
- Measured RTO: Pending
- Release recommendation: Pending
