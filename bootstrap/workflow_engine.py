from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class WorkflowEnginePlan:
    stages: tuple[str, ...]
    orchestration_modes: tuple[str, ...]
    task_boundaries: tuple[str, ...]
    execution_notes: str


def build_workflow_engine_plan(manifest: InfrastructureManifest) -> WorkflowEnginePlan:
    _ = manifest
    return WorkflowEnginePlan(
        stages=("plan", "route", "execute", "verify", "report"),
        orchestration_modes=("manual approval", "semi-automated", "fully automated"),
        task_boundaries=("safe local actions", "tool-mediated external actions", "approval-gated changes"),
        execution_notes="route tasks through explicit plans, keep dangerous actions approval-gated, and verify outputs before reporting",
    )


def render_workflow_engine_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_workflow_engine_plan(manifest)
    return {
        "stages": list(plan.stages),
        "orchestration_modes": list(plan.orchestration_modes),
        "task_boundaries": list(plan.task_boundaries),
        "execution_notes": plan.execution_notes,
    }
