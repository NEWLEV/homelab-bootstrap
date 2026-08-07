from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class AgentPlatformPlan:
    planners: tuple[str, ...]
    routers: tuple[str, ...]
    execution_layers: tuple[str, ...]
    memory_layers: tuple[str, ...]
    workflow_notes: str


def build_agent_platform_plan(manifest: InfrastructureManifest) -> AgentPlatformPlan:
    _ = manifest
    return AgentPlatformPlan(
        planners=("task planner", "workflow planner", "policy planner"),
        routers=("tool router", "model router", "skill router"),
        execution_layers=("local execution", "tool execution", "workflow execution"),
        memory_layers=("short-term memory", "project memory", "operational memory"),
        workflow_notes="start with explicit planning, route work through tools or skills, and keep memory backed by repository-managed artifacts",
    )


def render_agent_platform_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_agent_platform_plan(manifest)
    return {
        "planners": list(plan.planners),
        "routers": list(plan.routers),
        "execution_layers": list(plan.execution_layers),
        "memory_layers": list(plan.memory_layers),
        "workflow_notes": plan.workflow_notes,
    }
