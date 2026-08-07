from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .autonomous_ops import render_autonomous_ops_plan
from .diagnostics import render_diagnostics_plan
from .infrastructure import InfrastructureManifest
from .maintenance import render_maintenance_plan
from .repair_guide import render_repair_guide_plan
from .self_healing import render_self_healing_plan


@dataclass(frozen=True)
class OperationsSummaryPlan:
    diagnostics: dict[str, Any]
    repair_guide: dict[str, Any]
    maintenance: dict[str, Any]
    self_healing: dict[str, Any]
    summary_notes: str


def build_operations_summary_plan(manifest: InfrastructureManifest) -> OperationsSummaryPlan:
    diagnostics = render_diagnostics_plan(manifest)
    repair_guide = render_repair_guide_plan(manifest)
    maintenance = render_maintenance_plan(manifest)
    self_healing = render_self_healing_plan(manifest)
    autonomous = render_autonomous_ops_plan(manifest)
    return OperationsSummaryPlan(
        diagnostics=diagnostics,
        repair_guide=repair_guide,
        maintenance=maintenance,
        self_healing=self_healing,
        summary_notes=f"autonomous operations focus on {', '.join(autonomous['optimization_targets'])} while staying approval-gated for risky actions",
    )


def render_operations_summary_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_operations_summary_plan(manifest)
    return {
        "diagnostics": plan.diagnostics,
        "repair_guide": plan.repair_guide,
        "maintenance": plan.maintenance,
        "self_healing": plan.self_healing,
        "summary_notes": plan.summary_notes,
    }
