from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest
from .memory import render_memory_plan


@dataclass(frozen=True)
class PersistentMemoryPlan:
    storage_layers: tuple[str, ...]
    persistence_rules: tuple[str, ...]
    retention_policy: tuple[str, ...]
    restore_notes: str


def build_persistent_memory_plan(manifest: InfrastructureManifest) -> PersistentMemoryPlan:
    memory = render_memory_plan(manifest)
    _ = memory
    return PersistentMemoryPlan(
        storage_layers=("repository-backed summaries", "indexed vector store", "revision history"),
        persistence_rules=("store durable facts locally", "version every meaningful update", "prefer append-only history for traceability"),
        retention_policy=("keep conversation history short-term", "retain project and operational memory long-term", "prune stale or duplicate summaries"),
        restore_notes="restore durable memory before resuming long-lived assistant, project, or operations workflows",
    )


def render_persistent_memory_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_persistent_memory_plan(manifest)
    return {
        "storage_layers": list(plan.storage_layers),
        "persistence_rules": list(plan.persistence_rules),
        "retention_policy": list(plan.retention_policy),
        "restore_notes": plan.restore_notes,
    }
