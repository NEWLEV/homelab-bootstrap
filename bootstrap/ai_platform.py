from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai_services import render_ai_services_compose_yaml, render_ai_services_plan
from .ingestion import render_ingestion_plan
from .infrastructure import InfrastructureManifest
from .models import render_model_layer_plan
from .rag_api import render_rag_api_plan


@dataclass(frozen=True)
class AiPlatformPlan:
    services: tuple[str, ...]
    model_services: tuple[str, ...]
    storage_services: tuple[str, ...]
    workflow_steps: tuple[str, ...]
    integration_layers: tuple[str, ...]
    model_layer: dict[str, Any]
    service_layer: dict[str, Any]
    rag_api: dict[str, Any]
    ingestion: dict[str, Any]
    deployment_notes: str


def build_ai_platform_plan(manifest: InfrastructureManifest) -> AiPlatformPlan:
    model_layer = render_model_layer_plan(manifest)
    service_layer = render_ai_services_plan(manifest)
    rag_api = render_rag_api_plan(manifest)
    ingestion = render_ingestion_plan(manifest)
    return AiPlatformPlan(
        services=(
            "OpenClaw runtime",
            "local LLM service",
            "embedding service",
            "vector database",
            "RAG API",
            "tool execution framework",
            "n8n workflow orchestrator",
            "MCP tool gateway",
            "Skills registry",
        ),
        model_services=("local LLM service", "embedding service"),
        storage_services=("vector database",),
        workflow_steps=(
            "ingest documents",
            "chunk content",
            "embed chunks",
            "index vectors",
            "retrieve context",
            "generate grounded answers",
            "execute approved tools",
            "route durable automations through n8n",
            "invoke structured tools through MCP",
            "run reusable local procedures through Skills",
            "retrieve, rerank, generate, and cite through the RAG API",
            "discover, parse, chunk, embed, index, and verify source documents",
        ),
        integration_layers=(
            "n8n for durable orchestration",
            "MCP for structured tool access",
            "Skills for reusable local workflows",
        ),
        model_layer=model_layer,
        service_layer=service_layer,
        rag_api=rag_api,
        ingestion=ingestion,
        deployment_notes="deploy each service separately, then wire RAG, tools, n8n workflows, MCP gateways, and Skills on top of the shared infrastructure layer",
    )


def render_ai_platform_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_ai_platform_plan(manifest)
    return {
        "services": list(plan.services),
        "model_services": list(plan.model_services),
        "storage_services": list(plan.storage_services),
        "workflow_steps": list(plan.workflow_steps),
        "integration_layers": list(plan.integration_layers),
        "model_layer": plan.model_layer,
        "service_layer": plan.service_layer,
        "rag_api": plan.rag_api,
        "ingestion": plan.ingestion,
        "deployment_notes": plan.deployment_notes,
    }
