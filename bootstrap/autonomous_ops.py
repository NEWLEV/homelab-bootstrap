from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class AutonomousOpsPlan:
    diagnostics: tuple[str, ...]
    self_healing: tuple[str, ...]
    maintenance_recommendations: tuple[str, ...]
    optimization_targets: tuple[str, ...]
    approval_notes: str


def build_autonomous_ops_plan(manifest: InfrastructureManifest) -> AutonomousOpsPlan:
    _ = manifest
    return AutonomousOpsPlan(
        diagnostics=("container health", "log review", "backup verification", "certificate checks", "configuration drift"),
        self_healing=("restart unhealthy services", "repair broken compose stacks", "rebuild indexes", "retry transient jobs"),
        maintenance_recommendations=("upgrade dependencies", "rotate backups", "review alerts", "clean logs", "verify restores"),
        optimization_targets=("latency", "uptime", "storage efficiency", "resource usage"),
        approval_notes="automated actions should stay approval-gated when they are destructive, externally visible, or modify persistent state",
    )


def render_autonomous_ops_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_autonomous_ops_plan(manifest)
    return {
        "diagnostics": list(plan.diagnostics),
        "self_healing": list(plan.self_healing),
        "maintenance_recommendations": list(plan.maintenance_recommendations),
        "optimization_targets": list(plan.optimization_targets),
        "approval_notes": plan.approval_notes,
    }
