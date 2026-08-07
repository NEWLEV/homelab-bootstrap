from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class RagApiStep:
    name: str
    purpose: str
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class RagApiPlan:
    service: str
    steps: tuple[RagApiStep, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    boundary_notes: str


def build_rag_api_plan(manifest: InfrastructureManifest) -> RagApiPlan:
    _ = manifest
    return RagApiPlan(
        service="RAG API",
        steps=(
            RagApiStep(
                name="retrieve",
                purpose="fetch relevant context from the vector database",
                depends_on=("vector database",),
            ),
            RagApiStep(
                name="rerank",
                purpose="rank retrieved chunks for answer quality",
                depends_on=("retrieve",),
            ),
            RagApiStep(
                name="generate",
                purpose="ask the local LLM service to produce a grounded answer",
                depends_on=("rerank", "local LLM service"),
            ),
            RagApiStep(
                name="cite",
                purpose="attach source citations to the final response",
                depends_on=("generate",),
            ),
        ),
        inputs=("user question", "indexed vectors", "document metadata"),
        outputs=("grounded answer", "citations", "confidence notes"),
        boundary_notes="keep retrieval and generation on the internal network; expose only the RAG API surface if external access is explicitly approved",
    )


def render_rag_api_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_rag_api_plan(manifest)
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
        "boundary_notes": plan.boundary_notes,
    }
