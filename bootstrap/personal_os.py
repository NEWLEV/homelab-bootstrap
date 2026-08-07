from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .agent_platform import render_agent_platform_plan
from .ai_platform import render_ai_platform_plan
from .autonomous_ops import render_autonomous_ops_plan
from .integrations import render_integration_registry
from .infrastructure import InfrastructureManifest
from .memory import render_memory_plan
from .operations_summary import render_operations_summary_plan
from .skills import render_skills_plan


@dataclass(frozen=True)
class PersonalOsPlan:
    interface_layers: tuple[str, ...]
    assistant_modes: tuple[str, ...]
    memory_layers: dict[str, Any]
    operations_layers: dict[str, Any]
    integration_layers: dict[str, Any]
    roadmap_notes: str


def build_personal_os_plan(manifest: InfrastructureManifest) -> PersonalOsPlan:
    ai_platform = render_ai_platform_plan(manifest)
    agent_platform = render_agent_platform_plan(manifest)
    memory = render_memory_plan(manifest)
    operations = render_operations_summary_plan(manifest)
    integrations = render_integration_registry(manifest)
    skills = render_skills_plan(manifest)
    autonomous = render_autonomous_ops_plan(manifest)
    return PersonalOsPlan(
        interface_layers=("unified web interface", "conversational system management", "task routing", "policy and approvals"),
        assistant_modes=("development assistant", "research assistant", "infrastructure assistant", "personal productivity"),
        memory_layers={"agent": agent_platform, "memory": memory},
        operations_layers={"operations": operations, "autonomous_ops": autonomous},
        integration_layers={"integrations": integrations, "skills": skills, "ai_platform": ai_platform},
        roadmap_notes="Phase 6 unifies AI, agents, memory, operations, and integrations into a single personal operating surface while keeping approvals and provenance explicit",
    )


def render_personal_os_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_personal_os_plan(manifest)
    return {
        "interface_layers": list(plan.interface_layers),
        "assistant_modes": list(plan.assistant_modes),
        "memory_layers": plan.memory_layers,
        "operations_layers": plan.operations_layers,
        "integration_layers": plan.integration_layers,
        "roadmap_notes": plan.roadmap_notes,
    }
