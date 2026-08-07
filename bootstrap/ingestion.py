from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class IngestionStep:
    name: str
    purpose: str
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class IngestionPlan:
    service: str
    steps: tuple[IngestionStep, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    retry_notes: str
    boundary_notes: str


def build_ingestion_plan(manifest: InfrastructureManifest) -> IngestionPlan:
    _ = manifest
    return IngestionPlan(
        service="ingestion and indexing",
        steps=(
            IngestionStep(
                name="discover",
                purpose="find eligible local source files and documents",
                depends_on=(),
            ),
            IngestionStep(
                name="parse",
                purpose="extract text and structure from source files",
                depends_on=("discover",),
            ),
            IngestionStep(
                name="chunk",
                purpose="split content into manageable retrieval chunks",
                depends_on=("parse",),
            ),
            IngestionStep(
                name="embed",
                purpose="send chunks to the embedding service",
                depends_on=("chunk", "embedding service"),
            ),
            IngestionStep(
                name="index",
                purpose="persist vectors and metadata to the vector database",
                depends_on=("embed", "vector database"),
            ),
            IngestionStep(
                name="verify",
                purpose="check the indexed documents and record ingestion status",
                depends_on=("index",),
            ),
        ),
        inputs=("documents", "markdown", "pdfs", "notes", "internal files"),
        outputs=("chunks", "embeddings", "vector records", "ingestion status"),
        retry_notes="retry parse and embedding steps for transient failures; fail fast on invalid source documents",
        boundary_notes="keep ingestion local, write only to repository-backed storage and the private vector store, and avoid external publication during indexing",
    )


def render_ingestion_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_ingestion_plan(manifest)
    return {
        "service": plan.service,
        "steps": [
            {
                "name": step.name,
                "purpose": step.purpose,
                "depends_on": list(step.depends_on),
            }
            for step in plan.steps
        ],
        "inputs": list(plan.inputs),
        "outputs": list(plan.outputs),
        "retry_notes": plan.retry_notes,
        "boundary_notes": plan.boundary_notes,
    }
