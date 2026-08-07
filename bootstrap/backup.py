from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class BackupPlan:
    service: str
    volume_names: tuple[str, ...]
    schedule: str
    retention_policy: str
    restore_check: str
    hooks: dict[str, str]


def build_backup_plan(manifest: InfrastructureManifest) -> BackupPlan:
    return BackupPlan(
        service="backups",
        volume_names=manifest.volumes,
        schedule="daily",
        retention_policy="7 daily, 4 weekly, 6 monthly",
        restore_check="restore the latest snapshot into an isolated verification volume",
        hooks={
            "schedule": "daily snapshot rotation",
            "restore": "isolated verification restore",
        },
    )


def render_backup_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_backup_plan(manifest)
    return {
        "service": plan.service,
        "volume_names": list(plan.volume_names),
        "schedule": plan.schedule,
        "retention_policy": plan.retention_policy,
        "restore_check": plan.restore_check,
        "hooks": plan.hooks,
        "targets": [
            {
                "volume": volume_name,
                "path": f"/srv/data/services/{volume_name}",
            }
            for volume_name in plan.volume_names
        ],
    }
