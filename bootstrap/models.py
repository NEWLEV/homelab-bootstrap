from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ModelService:
    name: str
    role: str
    storage: str
    inference_notes: str


@dataclass(frozen=True)
class ModelLayerPlan:
    services: tuple[ModelService, ...]
    routing_notes: str
    deployment_notes: str


def build_model_layer_plan(manifest: InfrastructureManifest) -> ModelLayerPlan:
    _ = manifest
    return ModelLayerPlan(
        services=(
            ModelService(
                name="local LLM service",
                role="generation and reasoning",
                storage="model weights stored on local persistent disk",
                inference_notes="serve locally to keep prompts and outputs private",
            ),
            ModelService(
                name="embedding service",
                role="vector generation",
                storage="embedding model weights stored on local persistent disk",
                inference_notes="batch or stream embeddings for ingestion and incremental updates",
            ),
        ),
        routing_notes="route generation to the local LLM service and embedding jobs to the embedding service before crossing any external boundary",
        deployment_notes="deploy model services alongside the shared infrastructure layer with explicit persistent storage and local-only access by default",
    )


def render_model_layer_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_model_layer_plan(manifest)
    return {
        "services": [
            {
                "name": service.name,
                "role": service.role,
                "storage": service.storage,
                "inference_notes": service.inference_notes,
            }
            for service in plan.services
        ],
        "routing_notes": plan.routing_notes,
        "deployment_notes": plan.deployment_notes,
    }
