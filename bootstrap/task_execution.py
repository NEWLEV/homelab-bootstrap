from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class TaskExecutionPlan:
    task_states: tuple[str, ...]
    handoff_rules: tuple[str, ...]
    verification_steps: tuple[str, ...]
    notes: str


def build_task_execution_plan(manifest: InfrastructureManifest) -> TaskExecutionPlan:
    _ = manifest
    return TaskExecutionPlan(
        task_states=("queued", "planned", "running", "verified", "completed"),
        handoff_rules=("handoff after planning", "request approval before external side effects", "record outcomes before completion"),
        verification_steps=("check outputs", "check logs", "check citations", "confirm memory updates"),
        notes="keep each task traceable from plan to execution and back to durable records",
    )


def render_task_execution_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_task_execution_plan(manifest)
    return {
        "task_states": list(plan.task_states),
        "handoff_rules": list(plan.handoff_rules),
        "verification_steps": list(plan.verification_steps),
        "notes": plan.notes,
    }
