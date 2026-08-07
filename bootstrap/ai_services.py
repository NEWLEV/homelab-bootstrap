from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class AiService:
    name: str
    role: str
    depends_on: tuple[str, ...]
    persistence: str
    access: str


@dataclass(frozen=True)
class AiServicesPlan:
    services: tuple[AiService, ...]
    deployment_order: tuple[str, ...]
    boundary_notes: str


def build_ai_services_plan(manifest: InfrastructureManifest) -> AiServicesPlan:
    _ = manifest
    services = (
        AiService(
            name="local LLM service",
            role="generation and reasoning",
            depends_on=(),
            persistence="model weights on local persistent storage",
            access="local network only",
        ),
        AiService(
            name="embedding service",
            role="vector generation",
            depends_on=(),
            persistence="embedding model weights on local persistent storage",
            access="local network only",
        ),
        AiService(
            name="vector database",
            role="persistent vector storage",
            depends_on=("embedding service",),
            persistence="indexed vectors and metadata on durable disk",
            access="private internal network",
        ),
        AiService(
            name="RAG API",
            role="retrieval and grounded response orchestration",
            depends_on=("local LLM service", "embedding service", "vector database"),
            persistence="stateless service using the other layers",
            access="private internal network with optional reverse-proxy exposure",
        ),
    )
    return AiServicesPlan(
        services=services,
        deployment_order=("local LLM service", "embedding service", "vector database", "RAG API"),
        boundary_notes="deploy AI services behind the shared infrastructure layer, keep model and vector storage private, and expose only the RAG API if needed",
    )


def render_ai_services_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_ai_services_plan(manifest)
    return {
        "services": [
            {
                "name": service.name,
                "role": service.role,
                "depends_on": list(service.depends_on),
                "persistence": service.persistence,
                "access": service.access,
            }
            for service in plan.services
        ],
        "deployment_order": list(plan.deployment_order),
        "boundary_notes": plan.boundary_notes,
    }


def render_ai_services_compose_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = render_ai_services_plan(manifest)
    services = {}
    for service in plan["services"]:
        definition: dict[str, Any] = {
            "depends_on": list(service["depends_on"]),
            "networks": ["internal"],
            "environment": {
                "AISHA_SERVICE_ROLE": service["role"],
                "AISHA_SERVICE_ACCESS": service["access"],
            },
        }
        if service["name"] == "local LLM service":
            definition["image"] = "local/llm:latest"
            definition["volumes"] = ["llm-model-data:/models"]
        elif service["name"] == "embedding service":
            definition["image"] = "local/embeddings:latest"
            definition["volumes"] = ["embedding-model-data:/models"]
        elif service["name"] == "vector database":
            definition["image"] = "qdrant/qdrant:latest"
            definition["volumes"] = ["vector-db-data:/qdrant/storage"]
        elif service["name"] == "RAG API":
            definition["image"] = "local/rag-api:latest"
            definition["ports"] = ["8088:8088"]
        services[service["name"]] = definition

    return {
        "name": "aisha-ai-services",
        "services": services,
        "volumes": {
            "llm-model-data": {},
            "embedding-model-data": {},
            "vector-db-data": {},
        },
        "networks": {
            "internal": {},
        },
        "boundary_notes": plan["boundary_notes"],
    }


def render_ai_services_compose_yaml(manifest: InfrastructureManifest) -> str:
    compose_plan = render_ai_services_compose_plan(manifest)
    return yaml.safe_dump(
        {
            "name": compose_plan["name"],
            "services": compose_plan["services"],
            "volumes": compose_plan["volumes"],
            "networks": compose_plan["networks"],
            "x-aisha-boundary-notes": compose_plan["boundary_notes"],
        },
        sort_keys=False,
    )
