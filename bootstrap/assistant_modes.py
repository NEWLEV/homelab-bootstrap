from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class AssistantModesPlan:
    modes: tuple[str, ...]
    responsibilities: tuple[str, ...]
    guardrails: tuple[str, ...]
    notes: str


def build_assistant_modes_plan(manifest: InfrastructureManifest) -> AssistantModesPlan:
    _ = manifest
    return AssistantModesPlan(
        modes=("development assistant", "research assistant", "infrastructure assistant", "personal productivity"),
        responsibilities=("code and test work", "knowledge and synthesis", "platform and operations", "planning and follow-through"),
        guardrails=("preserve provenance", "ask before risky changes", "prefer explicit plans", "keep outputs reviewable"),
        notes="assistant modes should feel specialized while sharing memory, operations, and approval conventions",
    )


def render_assistant_modes_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_assistant_modes_plan(manifest)
    return {
        "modes": list(plan.modes),
        "responsibilities": list(plan.responsibilities),
        "guardrails": list(plan.guardrails),
        "notes": plan.notes,
    }
