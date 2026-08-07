from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class MaintenancePlan:
    tasks: tuple[str, ...]
    cadence: tuple[str, ...]
    checks: tuple[str, ...]
    notes: str


def build_maintenance_plan(manifest: InfrastructureManifest) -> MaintenancePlan:
    _ = manifest
    return MaintenancePlan(
        tasks=("rotate backups", "review alerts", "clean logs", "verify restores", "upgrade dependencies"),
        cadence=("daily", "weekly", "monthly"),
        checks=("service health", "restore success", "certificate freshness", "disk usage", "search quality"),
        notes="prefer recurring preventative maintenance before reactive repair work and keep every change reviewable",
    )


def render_maintenance_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_maintenance_plan(manifest)
    return {
        "tasks": list(plan.tasks),
        "cadence": list(plan.cadence),
        "checks": list(plan.checks),
        "notes": plan.notes,
    }
