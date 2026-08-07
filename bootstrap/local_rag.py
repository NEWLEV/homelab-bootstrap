from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ingestion import render_ingestion_plan
from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class LocalRagPlan:
    components: tuple[str, ...]
    capabilities: tuple[str, ...]
    data_flow: tuple[str, ...]
    storage_plan: dict[str, str]
    ingestion: dict[str, Any]
    roadmap_items: tuple[str, ...]
    deployment_notes: str


def build_local_rag_plan(manifest: InfrastructureManifest) -> LocalRagPlan:
    ingestion = render_ingestion_plan(manifest)
    return LocalRagPlan(
        components=(
            "document parser",
            "chunker",
            "embedding service",
            "vector database",
            "retrieval API",
            "grounded answer generator",
            "citation extractor",
            "local reranker",
        ),
        capabilities=(
            "document parsing",
            "chunking",
            "embeddings",
            "vector search",
            "metadata filtering",
            "grounded answers",
        ),
        data_flow=(
            "ingest source files",
            "split content into chunks",
            "embed chunks",
            "store vectors and metadata",
            "retrieve candidates",
            "rerank candidates",
            "generate grounded response",
            "attach citations",
        ),
        storage_plan={
            "backend": "persistent vector store",
            "location": "/srv/data/services/vector-database",
            "retention": "keep indexed vectors, metadata, and embedding state on durable storage",
            "restore": "restore the vector store before resuming retrieval or answer generation",
        },
        ingestion=ingestion,
        roadmap_items=(
            "hybrid search",
            "cross-document reasoning",
            "citation ranking",
            "incremental updates",
            "multiple embedding models",
        ),
        deployment_notes="run the local RAG service beside the shared infrastructure layer so retrieval, embeddings, and generation remain private and reproducible",
    )


def render_local_rag_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_local_rag_plan(manifest)
    return {
        "components": list(plan.components),
        "capabilities": list(plan.capabilities),
        "data_flow": list(plan.data_flow),
        "storage_plan": plan.storage_plan,
        "ingestion": plan.ingestion,
        "roadmap_items": list(plan.roadmap_items),
        "deployment_notes": plan.deployment_notes,
    }
