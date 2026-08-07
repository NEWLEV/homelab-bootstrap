from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest
from .persistent_memory import render_persistent_memory_plan


@dataclass(frozen=True)
class KnowledgeGraphPlan:
    entities: tuple[str, ...]
    relationships: tuple[str, ...]
    provenance_rules: tuple[str, ...]
    traversal_notes: str


def build_knowledge_graph_plan(manifest: InfrastructureManifest) -> KnowledgeGraphPlan:
    persistent_memory = render_persistent_memory_plan(manifest)
    _ = persistent_memory
    return KnowledgeGraphPlan(
        entities=("people", "projects", "repositories", "documents", "tasks", "services"),
        relationships=("depends on", "references", "belongs to", "summarizes", "triggers"),
        provenance_rules=("store source references with every edge", "prefer repository-backed facts", "record confidence and timestamp for derived links"),
        traversal_notes="start from a user, project, or document and walk outward through relationships while preserving provenance",
    )


def render_knowledge_graph_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_knowledge_graph_plan(manifest)
    return {
        "entities": list(plan.entities),
        "relationships": list(plan.relationships),
        "provenance_rules": list(plan.provenance_rules),
        "traversal_notes": plan.traversal_notes,
    }
