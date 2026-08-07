from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ProductivityPlan:
    goals: tuple[str, ...]
    planning_loops: tuple[str, ...]
    focus_modes: tuple[str, ...]
    task_flow: tuple[str, ...]
    notes: str


def build_productivity_plan(manifest: InfrastructureManifest) -> ProductivityPlan:
    _ = manifest
    return ProductivityPlan(
        goals=("daily priorities", "weekly planning", "project milestones", "follow-up reminders"),
        planning_loops=("capture", "prioritize", "schedule", "execute", "review"),
        focus_modes=("deep work", "short context switches", "low-friction task capture", "goal-aware reminders"),
        task_flow=("collect tasks", "group by project", "rank by urgency", "schedule focus blocks", "review completed work"),
        notes="personal productivity should help turn conversational intent into a repeatable planning loop with minimal overhead",
    )


def render_productivity_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_productivity_plan(manifest)
    return {
        "goals": list(plan.goals),
        "planning_loops": list(plan.planning_loops),
        "focus_modes": list(plan.focus_modes),
        "task_flow": list(plan.task_flow),
        "notes": plan.notes,
    }
