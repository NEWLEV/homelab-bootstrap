from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class MemoryPlan:
    memory_types: tuple[str, ...]
    storage: str
    retention_notes: str
    retrieval_notes: str


def build_memory_plan(manifest: InfrastructureManifest) -> MemoryPlan:
    _ = manifest
    return MemoryPlan(
        memory_types=("conversation", "preferences", "projects", "tasks", "documents"),
        storage="repository-backed summaries plus indexed vector storage",
        retention_notes="retain project and operational memory locally with explicit revision history",
        retrieval_notes="prefer indexed search first, then summarize from durable records and skill outputs",
    )


def render_memory_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_memory_plan(manifest)
    return {
        "memory_types": list(plan.memory_types),
        "storage": plan.storage,
        "retention_notes": plan.retention_notes,
        "retrieval_notes": plan.retrieval_notes,
    }
