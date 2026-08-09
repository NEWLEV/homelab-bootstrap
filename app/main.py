from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import chromadb
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from app.indexer import REQUIRED_METADATA_FIELDS, build_index_status
from app.reranker import LocalReranker
from app.retrieval import candidate_pool_size, rerank_candidates
from bootstrap.agent_platform import render_agent_platform_plan
from bootstrap.assistant_modes import render_assistant_modes_plan
from bootstrap.web_interface import render_web_interface_plan
from bootstrap.personal_os import render_personal_os_plan
from bootstrap.autonomous_ops import render_autonomous_ops_plan
from bootstrap.productivity import render_productivity_plan
from bootstrap.conversational_management import render_conversational_management_plan
from bootstrap.external_integrations import render_external_integration_plan
from bootstrap.knowledge_graph import render_knowledge_graph_plan
from bootstrap.home_automation import render_home_automation_plan
from bootstrap.diagnostics import render_diagnostics_plan
from bootstrap.operations_summary import render_operations_summary_plan
from bootstrap.self_healing import render_self_healing_plan
from bootstrap.maintenance import render_maintenance_plan
from bootstrap.repair_guide import render_repair_guide_plan
from bootstrap.ai_platform import render_ai_platform_plan
from bootstrap.ai_services import render_ai_services_compose_yaml, render_ai_services_plan
from bootstrap.memory import render_memory_plan
from bootstrap.persistent_memory import render_persistent_memory_plan
from bootstrap.task_execution import render_task_execution_plan
from bootstrap.workflow_engine import render_workflow_engine_plan
from bootstrap.ingestion import render_ingestion_plan
from bootstrap.integrations import render_integration_registry
from bootstrap.local_rag import render_local_rag_plan
from bootstrap.mcp import render_mcp_plan
from bootstrap.n8n import render_n8n_plan
from bootstrap.rag_api import render_rag_api_plan
from bootstrap.skills import render_skills_plan


APP_VERSION = "0.7.2"
REPO_ROOT = Path(__file__).resolve().parent.parent
HOMEPAGE_ASSET_DIR = REPO_ROOT / "configs" / "homepage"
MISSION_CONTROL_URL = os.environ.get("MISSION_CONTROL_URL", "http://127.0.0.1:8020").rstrip("/")
OPENCLAW_URL = os.environ.get("OPENCLAW_URL", "http://127.0.0.1:18790").rstrip("/")


app = FastAPI(
    title="Aisha Local RAG",
    version=APP_VERSION,
)


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/platform/web-dashboard", status_code=307)


CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", str(Path(tempfile.gettempdir()) / "aisha" / "chroma")))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDING_PROFILE = os.environ.get(
    "EMBEDDING_PROFILE",
    "balanced",
).strip().lower()
EMBEDDING_PROFILE_MAP = {
    "compact": {
        "model": "all-MiniLM-L6-v2",
        "fallbacks": ["nomic-embed-text"],
    },
    "balanced": {
        "model": "nomic-embed-text",
        "fallbacks": ["all-MiniLM-L6-v2", "bge-small-en-v1.5"],
    },
    "accurate": {
        "model": "bge-small-en-v1.5",
        "fallbacks": ["nomic-embed-text", "all-MiniLM-L6-v2"],
    },
}
EMBEDDING_PROFILE_NAME = EMBEDDING_PROFILE if EMBEDDING_PROFILE in EMBEDDING_PROFILE_MAP else "balanced"
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    EMBEDDING_PROFILE_MAP[EMBEDDING_PROFILE_NAME]["model"],
)
EMBEDDING_MODEL_FALLBACKS = [
    model.strip()
    for model in os.environ.get(
        "EMBEDDING_MODEL_FALLBACKS",
        ",".join(EMBEDDING_PROFILE_MAP[EMBEDDING_PROFILE_NAME]["fallbacks"]),
    ).split(",")
    if model.strip() and model.strip() != EMBEDDING_MODEL
]
GENERATION_MODEL = os.environ.get(
    "GENERATION_MODEL",
    "llama3.2:3b",
)
GENERATION_PROFILE = os.environ.get(
    "GENERATION_PROFILE",
    "balanced",
).strip().lower()
GENERATION_PROFILE_MAP = {
    "compact": {
        "temperature": 0.2,
        "max_tokens": 256,
        "top_p": 0.8,
    },
    "balanced": {
        "temperature": 0.4,
        "max_tokens": 512,
        "top_p": 0.9,
    },
    "accurate": {
        "temperature": 0.1,
        "max_tokens": 768,
        "top_p": 0.95,
    },
}
GENERATION_PROFILE_NAME = GENERATION_PROFILE if GENERATION_PROFILE in GENERATION_PROFILE_MAP else "balanced"

RERANKER_ENABLED = os.environ.get(
    "RERANKER_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes"}
RERANKER_MODEL = os.environ.get(
    "RERANKER_MODEL",
    "Xenova/ms-marco-MiniLM-L-6-v2",
)
RERANKER_CACHE_DIR = os.environ.get(
    "RERANKER_CACHE_DIR",
    "/models/fastembed",
)
RERANKER_THREADS = max(1, int(os.environ.get("RERANKER_THREADS", "2")))
reranker = LocalReranker(
    enabled=RERANKER_ENABLED,
    model_name=RERANKER_MODEL,
    cache_dir=RERANKER_CACHE_DIR,
    threads=RERANKER_THREADS,
)


INSUFFICIENT_CONTEXT_MESSAGE = (
    "The indexed repository does not contain enough information "
    "to answer this question."
)


CHROMA_PATH.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_PATH),
)

collection = chroma_client.get_or_create_collection(
    name="homelab_bootstrap",
    metadata={
        "description": "Aisha homelab repository",
    },
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    debug: bool = False
    path: str | None = None
    path_prefix: str | None = None
    directory: str | None = None
    directory_prefix: str | None = None
    extension: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)
    path: str | None = None
    debug: bool = False
    path_prefix: str | None = None
    directory: str | None = None
    directory_prefix: str | None = None
    extension: str | None = None


class Citation(BaseModel):
    path: str
    line_start: int
    line_end: int
    distance: float


class RetrievalDiagnostic(BaseModel):
    path: str
    line_start: int
    line_end: int
    distance: float
    vector_score: float
    lexical_score: float
    combined_score: float
    matching_tokens: list[str]
    rank: int
    hybrid_rank: int | None = None
    reranker_score: float | None = None
    reranker_used: bool = False
    reranker_error: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    citations: list[Citation]
    retrieval_debug: list[RetrievalDiagnostic] | None = None


class StatusResponse(BaseModel):
    status: str
    version: str
    vector_store: str
    collection: str
    chunks: int
    embedding_model: str
    embedding_model_fallbacks: list[str]
    embedding_profile: str
    generation_model: str
    generation_profile: str
    generation_options: dict[str, float | int]
    reranker_enabled: bool
    reranker_model: str
    reranker_threads: int
    retrieval_modes: list[str]
    capabilities: list[str]
    roadmap_items: list[str]


class IndexStatusResponse(BaseModel):
    collection: str
    chunks: int
    incremental_updates: bool
    metadata_migration_supported: bool
    content_hashing: bool
    stale_chunk_cleanup: bool
    embedding_profile: str
    required_metadata_fields: list[str]






class PlatformSummaryResponse(BaseModel):
    status: str
    ready: bool
    sections: list[str]
    ai_services: list[str]
    notes: list[str]

class PlatformStatusResponse(BaseModel):
    status: str
    sections: list[str]
    ai_platform: str
    ai_services: str
    rag_api: str
    ingestion: str
    local_rag: str
    integrations: list[str]
    notes: list[str]


class InfrastructureResponse(BaseModel):
    status: str
    manifest: str
    schema_path: str
    phase_names: list[str]
    service_order: list[str]
    volumes: list[str]
    networks: list[str]
    notes: list[str]


class StorageNetworkResponse(BaseModel):
    status: str
    storage: dict[str, Any]
    networking: dict[str, Any]


class MonitoringResponse(BaseModel):
    status: str
    service: str
    metric_targets: list[str]
    dashboard_expectations: list[str]
    alerting_targets: list[str]
    log_sources: list[str]
    collection_notes: str
    hooks: dict[str, list[str]]


class BackupResponse(BaseModel):
    status: str
    service: str
    volume_names: list[str]
    schedule: str
    retention_policy: str
    restore_check: str
    hooks: dict[str, str]
    targets: list[dict[str, str]]


class ExposureResponse(BaseModel):
    status: str
    service: str
    public_entrypoint: str
    tls_terminator: str
    dns_strategy: str
    exposed_services: list[str]
    internal_services: list[str]
    access_policy: dict[str, list[str]]
    boundary_notes: str


class DnsTlsResponse(BaseModel):
    status: str
    service: str
    dns_strategy: str
    tls_strategy: str
    certificate_source: str
    domain_boundaries: list[str]
    renewal_notes: str
    exposure_boundary: str


class RagApiResponse(BaseModel):
    status: str
    service: str
    steps: list[dict[str, Any]]
    inputs: list[str]
    outputs: list[str]
    boundary_notes: str


class IngestionResponse(BaseModel):
    status: str
    service: str
    steps: list[dict[str, Any]]
    inputs: list[str]
    outputs: list[str]
    retry_notes: str
    boundary_notes: str


class LocalRagResponse(BaseModel):
    status: str
    components: list[str]
    capabilities: list[str]
    data_flow: list[str]
    storage_plan: dict[str, str]
    ingestion: dict[str, Any]
    roadmap_items: list[str]
    deployment_notes: str


class SkillsResponse(BaseModel):
    status: str
    service: str
    skills: list[dict[str, str]]
    discovery_notes: str
    packaging_notes: str


class AgentPlatformResponse(BaseModel):
    status: str
    planners: list[str]
    routers: list[str]
    execution_layers: list[str]
    memory_layers: list[str]
    workflow_notes: str
    memory: dict[str, Any]


class MemoryResponse(BaseModel):
    status: str
    memory_types: list[str]
    storage: str
    retention_notes: str
    retrieval_notes: str


class PersistentMemoryResponse(BaseModel):
    status: str
    storage_layers: list[str]
    persistence_rules: list[str]
    retention_policy: list[str]
    restore_notes: str


class KnowledgeGraphResponse(BaseModel):
    status: str
    entities: list[str]
    relationships: list[str]
    provenance_rules: list[str]
    traversal_notes: str


class HomeAutomationResponse(BaseModel):
    status: str
    target_systems: list[str]
    control_surfaces: list[str]
    sensor_sources: list[str]
    safety_rules: list[str]
    notes: str


class ProductivityResponse(BaseModel):
    status: str
    goals: list[str]
    planning_loops: list[str]
    focus_modes: list[str]
    task_flow: list[str]
    notes: str


class AssistantModesResponse(BaseModel):
    status: str
    modes: list[str]
    responsibilities: list[str]
    guardrails: list[str]
    notes: str


class ExternalIntegrationsResponse(BaseModel):
    status: str
    systems: list[str]
    use_cases: list[str]
    control_modes: list[str]
    safety_rules: list[str]
    webhook_targets: list[dict[str, str]]
    setup_flow: list[str]
    notes: str


class WebDashboardResponse(BaseModel):
    status: str
    title: str
    sections: list[str]
    summary: str


class WorkflowEngineResponse(BaseModel):
    status: str
    stages: list[str]
    orchestration_modes: list[str]
    task_boundaries: list[str]
    execution_notes: str


class TaskExecutionResponse(BaseModel):
    status: str
    task_states: list[str]
    handoff_rules: list[str]
    verification_steps: list[str]
    notes: str


class AutonomousOpsResponse(BaseModel):
    status: str
    diagnostics: list[str]
    self_healing: list[str]
    maintenance_recommendations: list[str]
    optimization_targets: list[str]
    approval_notes: str


class RepairGuideResponse(BaseModel):
    status: str
    issue_classes: list[str]
    recommended_actions: list[str]
    escalation_rules: list[str]
    verification_checks: list[str]


class MaintenanceResponse(BaseModel):
    status: str
    tasks: list[str]
    cadence: list[str]
    checks: list[str]
    notes: str


class SelfHealingResponse(BaseModel):
    status: str
    triggers: list[str]
    phases: list[str]
    repair_actions: list[str]
    verification_steps: list[str]
    escalation_rules: list[str]


class DiagnosticsResponse(BaseModel):
    status: str
    checks: list[str]
    signals: list[str]
    baselines: list[str]
    notes: str


class OperationsSummaryResponse(BaseModel):
    status: str
    diagnostics: dict[str, Any]
    repair_guide: dict[str, Any]
    maintenance: dict[str, Any]
    self_healing: dict[str, Any]
    summary_notes: str


class PersonalOsResponse(BaseModel):
    status: str
    interface_layers: list[str]
    assistant_modes: list[str]
    memory_layers: dict[str, Any]
    operations_layers: dict[str, Any]
    integration_layers: dict[str, Any]
    roadmap_notes: str


class WebInterfaceResponse(BaseModel):
    status: str
    pages: list[str]
    dashboard_sections: list[str]
    entrypoints: list[str]
    navigation_notes: str
    personal_os: dict[str, Any]


class ConversationalManagementResponse(BaseModel):
    status: str
    intents: list[str]
    managed_domains: list[str]
    response_modes: list[str]
    escalation_rules: list[str]
    notes: str


class AiServicesResponse(BaseModel):
    status: str
    services: list[dict[str, Any]]
    deployment_order: list[str]
    boundary_notes: str
    compose_name: str
    compose_services: list[str]


class CapabilitiesResponse(BaseModel):
    status: str
    collection: str
    retrieval: dict[str, Any]
    indexing: dict[str, Any]
    profiles: dict[str, Any]


class ReadinessResponse(BaseModel):
    status: str
    ready: bool
    collection: str
    chunks: int
    vector_store_ready: bool
    retrieval_ready: bool
    indexing_ready: bool
    profile_ready: bool
    notes: list[str]


class MetricsResponse(BaseModel):
    status: str
    collection: str
    chunks: int
    ready: bool
    vector_store_ready: bool
    retrieval_modes: list[str]
    indexed_features: list[str]
    profiles: dict[str, Any]


class SummaryResponse(BaseModel):
    status: str
    collection: str
    ready: bool
    sources: int
    chunks: int
    question: str | None = None
    best_source: dict[str, Any] | None = None
    best_source_reason: str | None = None
    grouped_sources: list[dict[str, Any]] | None = None
    notes: list[str]
    retrieval_modes: list[str]
    profiles: dict[str, Any]


CITATION_PATTERN = re.compile(r"\[(\d+)(?:\.(\d+))?\]")


def build_grounded_prompt(question: str, matches: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        grouped.setdefault(str(match["path"]), []).append(match)

    context_blocks: list[str] = []
    for source_index, (path, source_matches) in enumerate(grouped.items(), start=1):
        block_lines = [f"Source {source_index}: {path}"]
        for chunk_index, match in enumerate(source_matches, start=1):
            block_lines.append(
                f"  [{source_index}.{chunk_index}] {match['line_start']}-{match['line_end']} {match.get('snippet', '')}"
            )
        context_blocks.append("\n".join(block_lines))

    context = "\n\n".join(context_blocks)
    return (
        "Answer the question using only the provided context. "
        "Reason across multiple chunks from the same source when helpful. "
        "Cite sources inline using [n.m].\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}"
    )


def _embedding_models() -> list[str]:
    return [EMBEDDING_MODEL, *EMBEDDING_MODEL_FALLBACKS]


def _embed_once(model: str, text: str) -> list[float]:
    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": model,
            "input": text,
        },
        timeout=120,
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings", [])
    if not embeddings:
        raise RuntimeError("Ollama returned no embedding.")
    return embeddings[0]


def embed_text(text: str) -> list[float]:
    last_error: Exception | None = None
    for model in _embedding_models():
        try:
            return _embed_once(model, text)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"All embedding models failed: {last_error}")


def generate_answer(prompt: str) -> str:
    generation_config = GENERATION_PROFILE_MAP[GENERATION_PROFILE_NAME]
    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": GENERATION_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": generation_config["temperature"],
                "num_predict": generation_config["max_tokens"],
                "top_p": generation_config["top_p"],
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    return str(body.get("response", "")).strip()


def is_insufficient_answer(answer: str) -> bool:
    normalized = answer.strip().lower()
    return not normalized or "insufficient" in normalized or "not enough information" in normalized


def extract_used_citations(answer: str, matches: list[dict[str, Any]]) -> list[Citation]:
    cited_indexes = []
    for source_index, chunk_index in CITATION_PATTERN.findall(answer):
        cited_indexes.append((int(source_index), int(chunk_index) if chunk_index else None))
    if not cited_indexes:
        return []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for match in matches:
        grouped.setdefault(str(match["path"]), []).append(match)

    answer_tokens = set(re.findall(r"[A-Za-z0-9]+", answer.lower()))
    ranked: list[tuple[float, Citation]] = []
    seen: set[tuple[int, int | None]] = set()
    ordered_paths = list(grouped)
    for source_index, chunk_index in cited_indexes:
        key = (source_index, chunk_index)
        if key in seen or source_index < 1 or source_index > len(ordered_paths):
            continue
        seen.add(key)
        path = ordered_paths[source_index - 1]
        source_matches = grouped[path]
        match = source_matches[(chunk_index - 1) if chunk_index else 0]
        snippet_tokens = set(re.findall(r"[A-Za-z0-9]+", f"{match.get('path', '')} {match.get('snippet', '')}".lower()))
        overlap = len(answer_tokens & snippet_tokens)
        citation = Citation(
            path=match["path"],
            line_start=match["line_start"],
            line_end=match["line_end"],
            distance=match["distance"],
        )
        ranked.append((float(overlap), citation))

    ranked.sort(key=lambda item: (item[0], -item[1].distance), reverse=True)
    return [citation for _, citation in ranked]


def build_metadata_filter(
    *,
    path: str | None = None,
    path_prefix: str | None = None,
    directory: str | None = None,
    directory_prefix: str | None = None,
    extension: str | None = None,
) -> dict[str, Any] | None:
    conditions: list[dict[str, Any]] = []

    if path:
        conditions.append(
            {
                "path": {
                    "$eq": path,
                },
            }
        )

    if path_prefix:
        conditions.append(
            {
                "path": {
                    "$contains": path_prefix,
                },
            }
        )

    if directory:
        conditions.append(
            {
                "directory": {
                    "$eq": directory,
                },
            }
        )

    if directory_prefix:
        conditions.append(
            {
                "directory": {
                    "$contains": directory_prefix,
                },
            }
        )

    if extension:
        conditions.append(
            {
                "extension": {
                    "$eq": extension,
                },
            }
        )

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {
        "$and": conditions,
    }


def retrieve_chunks(
    query: str,
    limit: int,
    debug: bool = False,
    path: str | None = None,
    path_prefix: str | None = None,
    directory: str | None = None,
    directory_prefix: str | None = None,
    extension: str | None = None,
) -> list[dict[str, Any]]:
    pool_size = candidate_pool_size(
        limit,
        collection.count(),
    )

    if pool_size == 0:
        return []

    query_embedding = embed_text(query)

    where = build_metadata_filter(
        path=path,
        path_prefix=path_prefix,
        directory=directory,
        directory_prefix=directory_prefix,
        extension=extension,
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=pool_size,
        include=["documents", "metadatas", "distances"],
        where=where,
    )

    matches: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, record_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) else {}
        document = documents[index] if index < len(documents) else ""
        match: dict[str, Any] = {
            "id": record_id,
            "path": metadata.get("path", record_id),
            "line_start": metadata.get("line_start", 1),
            "line_end": metadata.get("line_end", metadata.get("line_start", 1)),
            "distance": float(distances[index]) if index < len(distances) else 0.0,
            "snippet": document,
        }
        matches.append(match)

    return rerank_candidates(
        query=query,
        matches=matches,
        limit=limit,
        debug=debug,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "vector_store": "chromadb",
        "version": APP_VERSION,
        "collection": collection.name,
        "chunks": collection.count(),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_profile": EMBEDDING_PROFILE_NAME,
        "generation_model": GENERATION_MODEL,
        "generation_profile": GENERATION_PROFILE_NAME,
        "generation_options": GENERATION_PROFILE_MAP[GENERATION_PROFILE_NAME],
        "reranker_enabled": reranker.enabled,
        "reranker_model": reranker.model_name,
        "reranker_threads": reranker.threads,
    }


@app.get("/platform")
def platform() -> dict[str, Any]:
    return {
        "status": "ok",
        "ai_platform": render_ai_platform_plan(None),
        "ai_services": render_ai_services_plan(None),
        "ai_services_compose": render_ai_services_compose_yaml(None),
        "rag_api": render_rag_api_plan(None),
        "ingestion": render_ingestion_plan(None),
        "local_rag": render_local_rag_plan(None),
        "integrations": render_integration_registry(None),
        "n8n": render_n8n_plan(None),
        "mcp": render_mcp_plan(None),
        "skills": render_skills_plan(None),
    }


@app.get("/platform/integrations", response_model=dict[str, Any])
def platform_integrations() -> dict[str, Any]:
    return {
        "status": "ok",
        "integrations": render_integration_registry(None),
        "n8n": render_n8n_plan(None),
        "mcp": render_mcp_plan(None),
        "skills": render_skills_plan(None),
    }


@app.get("/platform/services", response_model=AiServicesResponse)
def platform_services() -> AiServicesResponse:
    plan = render_ai_services_plan(None)
    _ = render_ai_services_compose_yaml(None)
    return AiServicesResponse(
        status="ok",
        services=plan["services"],
        deployment_order=plan["deployment_order"],
        boundary_notes=plan["boundary_notes"],
        compose_name="aisha-ai-services",
        compose_services=["local LLM service", "embedding service", "vector database", "RAG API"],
    )


@app.get("/platform/infrastructure", response_model=InfrastructureResponse)
def platform_infrastructure() -> InfrastructureResponse:
    manifest = {
        "manifest": "infrastructure",
        "schema_path": "bootstrap/infrastructure.schema.json",
        "phase_names": ["storage", "networking", "monitoring", "backups", "exposure"],
        "service_order": ["reverse-proxy", "storage", "monitoring", "backups"],
        "volumes": ["prometheus-data", "backup-data"],
        "networks": ["edge", "internal"],
        "notes": [
            "Phase 2 infrastructure is described by the checked-in manifest and schema.",
            "The bootstrap CLI validates manifests before generating compose and readiness artifacts.",
        ],
    }
    return InfrastructureResponse(status="ok", **manifest)


@app.get("/platform/storage-network", response_model=StorageNetworkResponse)
def platform_storage_network() -> StorageNetworkResponse:
    return StorageNetworkResponse(
        status="ok",
        storage={
            "root": "/srv/data/services",
            "volumes": ["prometheus-data", "backup-data"],
            "volume_paths": {
                "prometheus-data": "/srv/data/services/prometheus-data",
                "backup-data": "/srv/data/services/backup-data",
            },
        },
        networking={
            "networks": ["edge", "internal"],
            "reverse_proxy_network": "edge",
            "internal_networks": ["internal"],
            "boundaries": {
                "public": ["edge"],
                "private": ["internal"],
            },
        },
    )


@app.get("/platform/monitoring", response_model=MonitoringResponse)
def platform_monitoring() -> MonitoringResponse:
    return MonitoringResponse(
        status="ok",
        service="monitoring",
        metric_targets=["cpu", "memory", "storage", "network", "service_health"],
        dashboard_expectations=["service availability", "request latency", "resource utilization"],
        alerting_targets=["containers", "healthchecks", "backups"],
        log_sources=["reverse-proxy", "monitoring", "backups"],
        collection_notes="monitor health and operational status without manual inspection",
        hooks={"scrape": ["metrics", "health", "logs"], "alert": ["containers", "healthchecks", "backups"]},
    )


@app.get("/platform/backups", response_model=BackupResponse)
def platform_backups() -> BackupResponse:
    return BackupResponse(
        status="ok",
        service="backups",
        volume_names=["prometheus-data", "backup-data"],
        schedule="daily",
        retention_policy="7 daily, 4 weekly, 6 monthly",
        restore_check="restore the latest snapshot into an isolated verification volume",
        hooks={"schedule": "daily snapshot rotation", "restore": "isolated verification restore"},
        targets=[
            {"volume": "prometheus-data", "path": "/srv/data/services/prometheus-data"},
            {"volume": "backup-data", "path": "/srv/data/services/backup-data"},
        ],
    )


@app.get("/platform/exposure", response_model=ExposureResponse)
def platform_exposure() -> ExposureResponse:
    return ExposureResponse(
        status="ok",
        service="reverse-proxy",
        public_entrypoint="edge",
        tls_terminator="traefik",
        dns_strategy="split-horizon or tunnel-backed external DNS",
        exposed_services=["reverse-proxy"],
        internal_services=["monitoring", "backups"],
        access_policy={"public": ["reverse-proxy"], "private": ["monitoring", "backups"]},
        boundary_notes="public services terminate at the edge proxy; all other services remain private on internal networks",
    )


@app.get("/platform/dns-tls", response_model=DnsTlsResponse)
def platform_dns_tls() -> DnsTlsResponse:
    return DnsTlsResponse(
        status="ok",
        service="reverse-proxy",
        dns_strategy="split-horizon DNS with optional tunnel fallback",
        tls_strategy="automatic TLS termination at the edge proxy",
        certificate_source="ACME-compatible provider or internal certificate authority",
        domain_boundaries=["public", "private"],
        renewal_notes="renew certificates before expiry and verify proxy reloads cleanly",
        exposure_boundary="public traffic terminates at edge; private services stay on internal networks",
    )


@app.get("/platform/rag-api", response_model=RagApiResponse)
def platform_rag_api() -> RagApiResponse:
    return RagApiResponse(
        status="ok",
        service="RAG API",
        steps=[
            {"name": "retrieve", "purpose": "fetch relevant context from the vector database", "depends_on": ["vector database"]},
            {"name": "rerank", "purpose": "rank retrieved chunks for answer quality", "depends_on": ["retrieve"]},
            {"name": "generate", "purpose": "ask the local LLM service to produce a grounded answer", "depends_on": ["rerank", "local LLM service"]},
            {"name": "cite", "purpose": "attach source citations to the final response", "depends_on": ["generate"]},
        ],
        inputs=["user question", "indexed vectors", "document metadata"],
        outputs=["grounded answer", "citations", "confidence notes"],
        boundary_notes="keep retrieval and generation on the internal network; expose only the RAG API surface if external access is explicitly approved",
    )


@app.get("/platform/ingestion", response_model=IngestionResponse)
def platform_ingestion() -> IngestionResponse:
    return IngestionResponse(
        status="ok",
        service="ingestion and indexing",
        steps=[
            {"name": "discover", "purpose": "find eligible local source files and documents", "depends_on": []},
            {"name": "parse", "purpose": "extract text and structure from source files", "depends_on": ["discover"]},
            {"name": "chunk", "purpose": "split content into manageable retrieval chunks", "depends_on": ["parse"]},
            {"name": "embed", "purpose": "send chunks to the embedding service", "depends_on": ["chunk", "embedding service"]},
            {"name": "index", "purpose": "persist vectors and metadata to the vector database", "depends_on": ["embed", "vector database"]},
            {"name": "verify", "purpose": "check the indexed documents and record ingestion status", "depends_on": ["index"]},
        ],
        inputs=["documents", "markdown", "pdfs", "notes", "internal files"],
        outputs=["chunks", "embeddings", "vector records", "ingestion status"],
        retry_notes="retry parse and embedding steps for transient failures; fail fast on invalid source documents",
        boundary_notes="keep ingestion local, write only to repository-backed storage and the private vector store, and avoid external publication during indexing",
    )


@app.get("/platform/local-rag", response_model=LocalRagResponse)
def platform_local_rag() -> LocalRagResponse:
    return LocalRagResponse(
        status="ok",
        components=["document parser", "chunker", "embedding service", "vector database", "retrieval API", "grounded answer generator", "citation extractor", "local reranker"],
        capabilities=["document parsing", "chunking", "embeddings", "vector search", "metadata filtering", "grounded answers"],
        data_flow=["ingest source files", "split content into chunks", "embed chunks", "store vectors and metadata", "retrieve candidates", "rerank candidates", "generate grounded response", "attach citations"],
        storage_plan={"backend": "persistent vector store", "location": "/srv/data/services/vector-database", "retention": "keep indexed vectors, metadata, and embedding state on durable storage", "restore": "restore the vector store before resuming retrieval or answer generation"},
        ingestion=render_ingestion_plan(None),
        roadmap_items=["hybrid search", "cross-document reasoning", "citation ranking", "incremental updates", "multiple embedding models"],
        deployment_notes="run the local RAG service beside the shared infrastructure layer so retrieval, embeddings, and generation remain private and reproducible",
    )


@app.get("/platform/skills", response_model=SkillsResponse)
def platform_skills() -> SkillsResponse:
    return SkillsResponse(
        status="ok",
        service="Skills registry",
        skills=[
            {"name": "bootstrap-validation", "category": "operations", "purpose": "run repeatable bootstrap checks and manifest validation flows", "invocation": "aisha skills run bootstrap-validation"},
            {"name": "integration-review", "category": "platform", "purpose": "summarize and validate n8n, MCP, and tool registry changes", "invocation": "aisha skills run integration-review"},
            {"name": "release-prep", "category": "devops", "purpose": "package repo changes, smoke tests, and rollout notes", "invocation": "aisha skills run release-prep"},
            {"name": "operator-checklist", "category": "operations", "purpose": "surface guided operator checklists for recurring maintenance tasks", "invocation": "aisha skills run operator-checklist"},
        ],
        discovery_notes="discover Skills from repository-backed manifests and keep them visible to automation, agents, and operators",
        packaging_notes="package Skills as repeatable local procedures with explicit metadata, versioning, and approval boundaries",
    )


@app.get("/platform/agent-platform", response_model=AgentPlatformResponse)
def platform_agent_platform() -> AgentPlatformResponse:
    memory = render_memory_plan(None)
    plan = render_agent_platform_plan(None)
    return AgentPlatformResponse(
        status="ok",
        planners=plan["planners"],
        routers=plan["routers"],
        execution_layers=plan["execution_layers"],
        memory_layers=plan["memory_layers"],
        workflow_notes=plan["workflow_notes"],
        memory=memory,
    )


@app.get("/platform/memory", response_model=MemoryResponse)
def platform_memory() -> MemoryResponse:
    plan = render_memory_plan(None)
    return MemoryResponse(
        status="ok",
        memory_types=plan["memory_types"],
        storage=plan["storage"],
        retention_notes=plan["retention_notes"],
        retrieval_notes=plan["retrieval_notes"],
    )


@app.get("/platform/persistent-memory", response_model=PersistentMemoryResponse)
def platform_persistent_memory() -> PersistentMemoryResponse:
    plan = render_persistent_memory_plan(None)
    return PersistentMemoryResponse(
        status="ok",
        storage_layers=plan["storage_layers"],
        persistence_rules=plan["persistence_rules"],
        retention_policy=plan["retention_policy"],
        restore_notes=plan["restore_notes"],
    )


@app.get("/platform/knowledge-graph", response_model=KnowledgeGraphResponse)
def platform_knowledge_graph() -> KnowledgeGraphResponse:
    plan = render_knowledge_graph_plan(None)
    return KnowledgeGraphResponse(
        status="ok",
        entities=plan["entities"],
        relationships=plan["relationships"],
        provenance_rules=plan["provenance_rules"],
        traversal_notes=plan["traversal_notes"],
    )


@app.get("/platform/home-automation", response_model=HomeAutomationResponse)
def platform_home_automation() -> HomeAutomationResponse:
    plan = render_home_automation_plan(None)
    return HomeAutomationResponse(
        status="ok",
        target_systems=plan["target_systems"],
        control_surfaces=plan["control_surfaces"],
        sensor_sources=plan["sensor_sources"],
        safety_rules=plan["safety_rules"],
        notes=plan["notes"],
    )


@app.get("/platform/productivity", response_model=ProductivityResponse)
def platform_productivity() -> ProductivityResponse:
    plan = render_productivity_plan(None)
    return ProductivityResponse(
        status="ok",
        goals=plan["goals"],
        planning_loops=plan["planning_loops"],
        focus_modes=plan["focus_modes"],
        task_flow=plan["task_flow"],
        notes=plan["notes"],
    )


@app.get("/platform/assistant-modes", response_model=AssistantModesResponse)
def platform_assistant_modes() -> AssistantModesResponse:
    plan = render_assistant_modes_plan(None)
    return AssistantModesResponse(
        status="ok",
        modes=plan["modes"],
        responsibilities=plan["responsibilities"],
        guardrails=plan["guardrails"],
        notes=plan["notes"],
    )


@app.get("/platform/external-integrations", response_model=ExternalIntegrationsResponse)
def platform_external_integrations() -> ExternalIntegrationsResponse:
    plan = render_external_integration_plan(None)
    return ExternalIntegrationsResponse(
        status="ok",
        systems=plan["systems"],
        use_cases=plan["use_cases"],
        control_modes=plan["control_modes"],
        safety_rules=plan["safety_rules"],
        webhook_targets=plan["webhook_targets"],
        setup_flow=plan["setup_flow"],
        notes=plan["notes"],
    )


@app.get("/platform/integration-webhooks", response_class=HTMLResponse)
def platform_integration_webhooks() -> HTMLResponse:
    plan = render_external_integration_plan(None)
    webhook_cards = ''.join(
        f"""
        <article class="card">
          <h2>{target['name']}</h2>
          <p><strong>Transport:</strong> {target['transport']}</p>
          <p><strong>Env var:</strong> <code>{target['env_var']}</code></p>
          <p><strong>Use case:</strong> {target['use_case']}</p>
          <p><strong>Example export:</strong> <code>{target['example_export']}</code></p>
        </article>
        """
        for target in plan["webhook_targets"]
    )
    setup_steps = ''.join(f'<li>{step}</li>' for step in plan['setup_flow'])
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aisha Integration Webhooks</title>
    <style>
      :root {{ color-scheme: dark; }}
      body {{ margin: 0; font-family: Inter, Segoe UI, system-ui, sans-serif; background: linear-gradient(160deg, #08111f, #111827 60%, #1f2937); color: #e5e7eb; }}
      .wrap {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px 64px; }}
      .hero, .card {{ background: rgba(17,24,39,.82); border: 1px solid rgba(148,163,184,.14); border-radius: 18px; padding: 20px; }}
      .hero {{ margin-bottom: 18px; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 18px; }}
      h1, h2 {{ margin: 0 0 12px; }}
      p, li {{ color: #cbd5e1; line-height: 1.6; }}
      code, pre {{ background: rgba(15,23,42,.88); color: #dbeafe; border-radius: 10px; }}
      code {{ padding: 0.15rem 0.35rem; }}
      pre {{ margin: 0; padding: 14px; overflow-x: auto; }}
      .links a {{ display: inline-block; margin: 6px 8px 0 0; padding: 8px 12px; border-radius: 999px; text-decoration: none; color: #bfdbfe; background: rgba(59,130,246,.16); border: 1px solid rgba(96,165,250,.22); }}
      ul {{ margin: 0; padding-left: 18px; }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="hero">
        <h1>Integration Webhooks</h1>
        <p>Use one shared setup flow for Slack, Discord, and Telegram. Aisha keeps the payload shape consistent so operators do not have to rebuild each integration from scratch.</p>
        <div class="links">
          <a href="/platform/web-dashboard">Back to dashboard</a>
          <a href="/platform/external-integrations">JSON view</a>
          <a href="/platform/mission-control">Mission Control</a>
        </div>
      </section>
      <section class="card">
        <h2>Setup Flow</h2>
        <ul>{setup_steps}</ul>
      </section>
      <section class="grid">{webhook_cards}</section>
      <section class="card" style="margin-top:18px;">
        <h2>Shared Payload</h2>
        <pre><code>{{
  "title": "Aisha test alert",
  "summary": "Integration webhook check",
  "detail": "This payload shape is shared across Slack, Discord, and Telegram examples.",
  "risk": "low"
}}</code></pre>
      </section>
      <section class="card" style="margin-top:18px;">
        <h2>Automatic Forwarding</h2>
        <p>Use <code>scripts/mission_control_webhook_dispatcher.py</code> to poll Mission Control and forward new events and pending approvals to any enabled target.</p>
        <pre><code>INTEGRATION_DISPATCH_ONCE=true python scripts/mission_control_webhook_dispatcher.py</code></pre>
      </section>
    </main>
  </body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/platform/workflow-engine", response_model=WorkflowEngineResponse)
def platform_workflow_engine() -> WorkflowEngineResponse:
    plan = render_workflow_engine_plan(None)
    return WorkflowEngineResponse(
        status="ok",
        stages=plan["stages"],
        orchestration_modes=plan["orchestration_modes"],
        task_boundaries=plan["task_boundaries"],
        execution_notes=plan["execution_notes"],
    )


@app.get("/platform/task-execution", response_model=TaskExecutionResponse)
def platform_task_execution() -> TaskExecutionResponse:
    plan = render_task_execution_plan(None)
    return TaskExecutionResponse(
        status="ok",
        task_states=plan["task_states"],
        handoff_rules=plan["handoff_rules"],
        verification_steps=plan["verification_steps"],
        notes=plan["notes"],
    )


@app.get("/platform/autonomous-ops", response_model=AutonomousOpsResponse)
def platform_autonomous_ops() -> AutonomousOpsResponse:
    plan = render_autonomous_ops_plan(None)
    return AutonomousOpsResponse(
        status="ok",
        diagnostics=plan["diagnostics"],
        self_healing=plan["self_healing"],
        maintenance_recommendations=plan["maintenance_recommendations"],
        optimization_targets=plan["optimization_targets"],
        approval_notes=plan["approval_notes"],
    )


@app.get("/platform/repair-guide", response_model=RepairGuideResponse)
def platform_repair_guide() -> RepairGuideResponse:
    plan = render_repair_guide_plan(None)
    return RepairGuideResponse(
        status="ok",
        issue_classes=plan["issue_classes"],
        recommended_actions=plan["recommended_actions"],
        escalation_rules=plan["escalation_rules"],
        verification_checks=plan["verification_checks"],
    )


@app.get("/platform/maintenance", response_model=MaintenanceResponse)
def platform_maintenance() -> MaintenanceResponse:
    plan = render_maintenance_plan(None)
    return MaintenanceResponse(
        status="ok",
        tasks=plan["tasks"],
        cadence=plan["cadence"],
        checks=plan["checks"],
        notes=plan["notes"],
    )


@app.get("/platform/self-healing", response_model=SelfHealingResponse)
def platform_self_healing() -> SelfHealingResponse:
    plan = render_self_healing_plan(None)
    return SelfHealingResponse(
        status="ok",
        triggers=plan["triggers"],
        phases=plan["phases"],
        repair_actions=plan["repair_actions"],
        verification_steps=plan["verification_steps"],
        escalation_rules=plan["escalation_rules"],
    )


@app.get("/platform/diagnostics", response_model=DiagnosticsResponse)
def platform_diagnostics() -> DiagnosticsResponse:
    plan = render_diagnostics_plan(None)
    return DiagnosticsResponse(
        status="ok",
        checks=plan["checks"],
        signals=plan["signals"],
        baselines=plan["baselines"],
        notes=plan["notes"],
    )


@app.get("/platform/operations-summary", response_model=OperationsSummaryResponse)
def platform_operations_summary() -> OperationsSummaryResponse:
    plan = render_operations_summary_plan(None)
    return OperationsSummaryResponse(
        status="ok",
        diagnostics=plan["diagnostics"],
        repair_guide=plan["repair_guide"],
        maintenance=plan["maintenance"],
        self_healing=plan["self_healing"],
        summary_notes=plan["summary_notes"],
    )


@app.get("/platform/personal-os", response_model=PersonalOsResponse)
def platform_personal_os() -> PersonalOsResponse:
    plan = render_personal_os_plan(None)
    return PersonalOsResponse(
        status="ok",
        interface_layers=plan["interface_layers"],
        assistant_modes=plan["assistant_modes"],
        memory_layers=plan["memory_layers"],
        operations_layers=plan["operations_layers"],
        integration_layers=plan["integration_layers"],
        roadmap_notes=plan["roadmap_notes"],
    )




@app.api_route(
    "/aisha",
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
@app.api_route(
    "/aisha/{path:path}",
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def openclaw_proxy(request: Request, path: str = "") -> Response:
    upstream_path = f"/aisha/{path}" if path else "/aisha"
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() in {"accept", "content-type"}
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                request.method,
                f"{OPENCLAW_URL}{upstream_path}",
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
    except httpx.HTTPError:
        return Response(
            content='{"detail":"Aisha chat is unavailable"}',
            status_code=503,
            media_type="application/json",
        )

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() in {
            "cache-control",
            "content-length",
            "content-security-policy",
            "content-type",
            "referrer-policy",
            "x-content-type-options",
        }
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )

@app.get("/mission-control/api/stream", include_in_schema=False)
async def mission_control_stream_proxy() -> StreamingResponse:
    async def relay():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{MISSION_CONTROL_URL}/api/stream") as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except httpx.HTTPError:
            yield b'event: error\ndata: {"detail":"Mission Control is unavailable"}\n\n'

    return StreamingResponse(
        relay(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.api_route(
    "/mission-control/{path:path}",
    methods=["GET", "POST", "DELETE"],
    include_in_schema=False,
)
async def mission_control_proxy(path: str, request: Request) -> Response:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() in {"content-type", "x-mission-control-token"}
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                request.method,
                f"{MISSION_CONTROL_URL}/{path}",
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
    except httpx.HTTPError:
        if not path:
            return HTMLResponse(
                "<h1>Mission Control unavailable</h1>"
                "<p>Start <code>aisha-mission-control.service</code> and reload.</p>",
                status_code=503,
            )
        return Response(
            content='{"detail":"Mission Control is unavailable"}',
            status_code=503,
            media_type="application/json",
        )

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() in {"content-type", "cache-control"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.get("/platform/mission-control", response_class=HTMLResponse)
def platform_mission_control() -> HTMLResponse:
    html = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Mission Control</title>
        <style>
          body {{ margin: 0; background: #111311; color: #f2f1ed; font: 16px/1.45 Inter, system-ui, sans-serif; }}
          .frame {{ padding: 16px; }}
          .wrap {{ max-width: 1440px; margin: 0 auto; }}
          .topbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 16px; flex-wrap: wrap; }}
          a {{ color: #7bc8a4; text-decoration: none; }}
        </style>
      </head>
      <body>
        <div class="frame">
          <div class="wrap">
            <div class="topbar">
              <div>
                <h1 style="margin:0 0 4px;font-size:28px;">Mission Control</h1>
                <div style="color:#a8a39b">Operational dashboard for agent activity, approvals, vitals, and digest replay.</div>
              </div>
              <a href="/platform/web-dashboard">Back to platform dashboard</a>
            </div>
            <iframe
              src="/mission-control/"
              title="Aisha Mission Control"
              style="display:block;width:100%;height:calc(100vh - 120px);min-height:680px;border:0;border-radius:16px;background:#111311;"
            ></iframe>
          </div>
        </div>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/platform/assets/aisha-launcher.js", include_in_schema=False)
def platform_aisha_launcher_script() -> Response:
    return Response(
        content=(HOMEPAGE_ASSET_DIR / "custom.js").read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/platform/assets/aisha-launcher.css", include_in_schema=False)
def platform_aisha_launcher_styles() -> Response:
    return Response(
        content=(HOMEPAGE_ASSET_DIR / "custom.css").read_text(encoding="utf-8"),
        media_type="text/css",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/platform/runbook", response_class=HTMLResponse)
def platform_runbook() -> HTMLResponse:
    html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aisha Runbook</title>
    <style>
      :root { color-scheme: dark; }
      body { margin: 0; font-family: Inter, Segoe UI, system-ui, sans-serif; background: linear-gradient(160deg, #08111f, #111827 60%, #1f2937); color: #e5e7eb; }
      .wrap { max-width: 920px; margin: 0 auto; padding: 40px 20px 64px; }
      .card { background: rgba(17,24,39,.82); border: 1px solid rgba(148,163,184,.14); border-radius: 18px; padding: 20px; margin-bottom: 16px; }
      h1, h2 { margin: 0 0 12px; }
      p, li { color: #cbd5e1; line-height: 1.6; }
      pre { margin: 0; padding: 14px; border-radius: 14px; overflow-x: auto; background: rgba(15,23,42,.88); color: #dbeafe; }
      code { background: rgba(15,23,42,.88); padding: 0.15rem 0.35rem; border-radius: 0.35rem; }
      .links a { display: inline-block; margin: 6px 8px 0 0; padding: 8px 12px; border-radius: 999px; text-decoration: none; color: #bfdbfe; background: rgba(59,130,246,.16); border: 1px solid rgba(96,165,250,.22); }
    </style>
  </head>
  <body>
    <main class="wrap">
      <div class="card">
        <h1>Aisha Runbook</h1>
        <p>Use these commands on Aisha to start the local RAG service safely and keep it running after reboot.</p>
      </div>
      <div class="card">
        <h2>Install boot auto-start</h2>
        <pre><code>cd /srv/data/git/homelab-bootstrap/workspaces/development/repo/services/local-rag
./scripts/install-local-rag-service.sh</code></pre>
      </div>
      <div class="card">
        <h2>Start or stop locally</h2>
        <pre><code>systemctl --user start aisha-local-rag.service
systemctl --user stop aisha-local-rag.service
systemctl --user restart aisha-local-rag.service
systemctl --user status aisha-local-rag.service</code></pre>
      </div>
      <div class="card">
        <h2>Manual launcher</h2>
        <pre><code>cd /srv/data/git/homelab-bootstrap/workspaces/development/repo/services/local-rag
source ~/.venvs/aisha/bin/activate
./scripts/run-local-rag.sh</code></pre>
      </div>
      <div class="card">
        <h2>Quick links</h2>
        <div class="links">
          <a href="/platform/web-dashboard">Dashboard</a>
          <a href="/docs">API Docs</a>
          <a href="/platform/personal-os">Personal OS</a>
          <a href="/platform/status">Status</a>
          <a href="/platform/summary">Summary</a>
        </div>
      </div>
    </main>
  </body>
</html>"""
    return HTMLResponse(content=html)
@app.get("/platform/web-dashboard", response_class=HTMLResponse)
def platform_web_dashboard() -> HTMLResponse:
    plan = render_web_interface_plan(None)
    personal_os = plan["personal_os"]
    sections = plan["dashboard_sections"]
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Aisha Dashboard</title>
    <link rel="stylesheet" href="/platform/assets/aisha-launcher.css" />
    <style>
      :root {{ color-scheme: dark; }}
      body {{ margin: 0; font-family: Inter, Segoe UI, system-ui, sans-serif; background: linear-gradient(160deg, #08111f, #111827 60%, #1f2937); color: #e5e7eb; }}
      .wrap {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px 64px; }}
      .hero {{ padding: 28px; border: 1px solid rgba(255,255,255,.08); border-radius: 24px; background: rgba(15,23,42,.72); box-shadow: 0 20px 60px rgba(0,0,0,.25); }}
      h1 {{ margin: 0 0 10px; font-size: 2.4rem; }}
      p {{ line-height: 1.6; color: #cbd5e1; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 20px; }}
      .card {{ background: rgba(17,24,39,.78); border: 1px solid rgba(148,163,184,.14); border-radius: 18px; padding: 18px; }}
      .card h2 {{ margin: 0 0 10px; font-size: 1rem; color: #f8fafc; text-transform: uppercase; letter-spacing: .08em; }}
      ul {{ margin: 0; padding-left: 18px; color: #dbeafe; }}
      li {{ margin: 6px 0; }}
      .pill {{ display: inline-block; margin: 6px 8px 0 0; padding: 6px 10px; border-radius: 999px; background: rgba(59,130,246,.16); color: #bfdbfe; font-size: .9rem; }}
      .muted {{ color: #94a3b8; }}
      .controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
      .controls a {{ display: inline-flex; align-items: center; justify-content: center; padding: 10px 14px; border-radius: 999px; border: 1px solid rgba(96,165,250,.35); background: rgba(37,99,235,.16); color: #dbeafe; text-decoration: none; font-weight: 700; }}
      .controls .secondary {{ background: rgba(15,23,42,.72); }}
      pre {{ margin: 0; padding: 14px; border-radius: 14px; overflow-x: auto; background: rgba(15,23,42,.88); color: #dbeafe; }}
      code {{ background: rgba(15,23,42,.88); padding: 0.15rem 0.35rem; border-radius: 0.35rem; }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="hero">
        <h1>Aisha Personal OS</h1>
        <p>unified web interface for the personal OS.</p>
        <p>{personal_os['roadmap_notes']}</p>
        <div>
          {''.join(f'<span class="pill">{mode}</span>' for mode in personal_os['assistant_modes'])}
        </div>
        <div class="controls" style="margin-top: 22px;">
          <a href="/platform/runbook">Runbook</a>
          <a href="/docs">API Docs</a>
          <a href="/platform/personal-os">Personal OS</a>
          <a href="/platform/status">Status</a>
          <a class="secondary" href="/platform/summary">Summary</a>
          <a class="secondary" href="/platform/web-interface">Web Interface</a>
        </div>
      </section>
      <section class="card" style="margin-top: 22px; border: 1px solid rgba(125,211,252,.45); background: linear-gradient(135deg, rgba(12,74,110,.92), rgba(30,41,59,.96)); box-shadow: 0 22px 50px rgba(2,132,199,.12);">
        <h2 style="margin:0 0 10px; text-transform: uppercase; letter-spacing: .08em; color: #e0f2fe;">Mission Control</h2>
        <p style="margin:0 0 14px; color: #dbeafe; max-width: 820px;">Open the operational dashboard for live agent activity, approvals, vitals, and the overnight digest. It stays local-only by default and sits behind the existing reverse proxy.</p>
        <div class="controls" style="margin-top: 0;">
          <a href="/platform/mission-control" style="background: linear-gradient(135deg, #7dd3fc, #2563eb); border-color: rgba(186,230,253,.9); color: #f8fafc; box-shadow: 0 14px 30px rgba(37,99,235,.28);">Open Mission Control</a>
        </div>
      </section>
      <section class="grid">
        <div class="card">
          <h2>Sections</h2>
          <ul>{''.join(f'<li>{section}</li>' for section in sections)}</ul>
        </div>
        <div class="card">
          <h2>Memory</h2>
          <ul>{''.join(f'<li>{item}</li>' for item in personal_os['memory_layers']['memory']['memory_types'])}</ul>
        </div>
        <div class="card">
          <h2>Operations</h2>
          <p>{personal_os['operations_layers']['operations']['summary_notes']}</p>
        </div>
        <div class="card">
          <h2>Integrations</h2>
          <ul>{''.join(f'<li>{entry["name"]}</li>' for entry in personal_os['integration_layers']['integrations']['entries'])}</ul>
          <div class="controls" style="margin-top: 14px;">
            <a class="secondary" href="/platform/integration-webhooks">Integration Webhooks</a>
          </div>
          <p class="muted" style="margin-top:12px;">Shared webhook exports now cover Slack, Discord, and Telegram with the same payload shape.</p>
        </div>
        <div class="card">
          <h2>Local RAG</h2>
          <p>Auto-start safely on boot with the user service:</p>
          <pre><code>cd /srv/data/git/homelab-bootstrap/workspaces/development/repo/services/local-rag
./scripts/install-local-rag-service.sh
systemctl --user start aisha-local-rag.service</code></pre>
        </div>
        <div class="card">
          <h2>Manual Actions</h2>
          <p>Use the dashboard as a control panel that shows commands rather than executing them remotely.</p>
          <pre><code>systemctl --user status aisha-local-rag.service
systemctl --user restart aisha-local-rag.service
./scripts/run-local-rag.sh</code></pre>
        </div>
      </section>
      <p class="muted" style="margin-top:24px">Dashboard sections: {', '.join(sections)}</p>
      <script src="/platform/assets/aisha-launcher.js" defer></script>
    </main>
  </body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/platform/web-interface", response_model=WebInterfaceResponse)
def platform_web_interface() -> WebInterfaceResponse:
    plan = render_web_interface_plan(None)
    return WebInterfaceResponse(
        status="ok",
        pages=plan["pages"],
        dashboard_sections=plan["dashboard_sections"],
        entrypoints=plan["entrypoints"],
        navigation_notes=plan["navigation_notes"],
        personal_os=plan["personal_os"],
    )



@app.get("/platform/conversational-management", response_model=ConversationalManagementResponse)
def platform_conversational_management() -> ConversationalManagementResponse:
    plan = render_conversational_management_plan(None)
    return ConversationalManagementResponse(
        status="ok",
        intents=plan["intents"],
        managed_domains=plan["managed_domains"],
        response_modes=plan["response_modes"],
        escalation_rules=plan["escalation_rules"],
        notes=plan["notes"],
    )


@app.post("/search")
def search(
    request: SearchRequest,
) -> dict[str, Any]:
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query must not be empty.",
        )

    try:
        matches = retrieve_chunks(
            query=query,
            limit=request.limit,
            debug=request.debug,
            path=request.path,
            path_prefix=request.path_prefix,
            directory=request.directory,
            directory_prefix=request.directory_prefix,
            extension=request.extension,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama embedding request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "query": query,
        "count": len(matches),
        "results": matches,
    }


@app.post(
    "/ask",
    response_model=AskResponse,
    response_model_exclude_none=True,
)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question must not be empty.",
        )

    try:
        matches = retrieve_chunks(
            query=question,
            limit=request.limit,
            debug=request.debug,
            path=request.path,
            path_prefix=request.path_prefix,
            directory=request.directory,
            directory_prefix=request.directory_prefix,
            extension=request.extension,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama embedding request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    retrieval_debug = (
        [
            RetrievalDiagnostic(
                path=match["path"],
                line_start=match["line_start"],
                line_end=match["line_end"],
                distance=match["distance"],
                vector_score=match["vector_score"],
                lexical_score=match["lexical_score"],
                combined_score=match["combined_score"],
                matching_tokens=match["matching_tokens"],
                rank=match["rank"],
                hybrid_rank=match.get("hybrid_rank"),
                reranker_score=match.get("reranker_score"),
                reranker_used=match.get("reranker_used", False),
                reranker_error=match.get("reranker_error"),
            )
            for match in matches
        ]
        if request.debug
        else None
    )
    if not matches:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    prompt = build_grounded_prompt(
        question,
        matches,
    )

    try:
        answer = generate_answer(prompt)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Ollama generation request failed: "
                f"{exc}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if is_insufficient_answer(answer):
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    citations = extract_used_citations(
        answer,
        matches,
    )

    if not citations:
        return AskResponse(
            question=question,
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            grounded=False,
            citations=[],
            retrieval_debug=retrieval_debug,
        )

    return AskResponse(
        question=question,
        answer=answer,
        grounded=True,
        citations=citations,
        retrieval_debug=retrieval_debug,
    )


@app.post("/index")
def index_documents() -> dict[str, Any]:
    from app.indexer import index_repository

    result = index_repository()

    return {
        "status": "indexed",
        **result,
    }


@app.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> CapabilitiesResponse:
    return CapabilitiesResponse(
        status="ok",
        collection=collection.name,
        retrieval={
            "modes": ["vector", "lexical", "hybrid"],
            "metadata_filters": ["path", "path_prefix", "directory", "directory_prefix", "extension"],
            "grounding": {
                "prompt_grouping": True,
                "citation_format": "[source.chunk]",
                "citation_ranking": True,
            },
        },
        indexing={
            "incremental_updates": True,
            "content_hashing": True,
            "stale_chunk_cleanup": True,
            "metadata_migration_supported": True,
            "required_metadata_fields": sorted(REQUIRED_METADATA_FIELDS),
        },
        profiles={
            "embedding": {
                "active": EMBEDDING_PROFILE_NAME,
                "model": EMBEDDING_MODEL,
                "fallbacks": EMBEDDING_MODEL_FALLBACKS,
            },
            "generation": {
                "active": GENERATION_PROFILE_NAME,
                "model": GENERATION_MODEL,
                "options": GENERATION_PROFILE_MAP[GENERATION_PROFILE_NAME],
            },
        },
    )


@app.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    capability_state = capabilities()
    health_state = health()
    index_state = index_status()
    ready_state = bool(health_state["chunks"] >= 0 and health_state["vector_store"] == "chromadb")
    return ReadinessResponse(
        status="ok",
        ready=ready_state,
        collection=collection.name,
        chunks=collection.count(),
        vector_store_ready=health_state["vector_store"] == "chromadb",
        retrieval_ready=bool(capability_state.retrieval["modes"]),
        indexing_ready=bool(index_state.required_metadata_fields),
        profile_ready=bool(EMBEDDING_PROFILE_NAME and GENERATION_PROFILE_NAME),
        notes=[
            "Vector store is reachable.",
            "Retrieval and indexing capabilities are exposed.",
            "Embedding and generation profiles are selected.",
        ],
    )


@app.get("/metrics", response_model=MetricsResponse)
def metrics() -> MetricsResponse:
    ready_state = ready()
    capability_state = capabilities()
    index_state = index_status()
    return MetricsResponse(
        status="ok",
        collection=collection.name,
        chunks=collection.count(),
        ready=ready_state.ready,
        vector_store_ready=ready_state.vector_store_ready,
        retrieval_modes=list(capability_state.retrieval["modes"]),
        indexed_features=[
            "incremental_updates",
            "content_hashing",
            "stale_chunk_cleanup",
            "metadata_migration",
        ],
        profiles={
            "embedding": {
                "active": EMBEDDING_PROFILE_NAME,
                "model": EMBEDDING_MODEL,
                "fallbacks": EMBEDDING_MODEL_FALLBACKS,
            },
            "generation": {
                "active": GENERATION_PROFILE_NAME,
                "model": GENERATION_MODEL,
                "options": GENERATION_PROFILE_MAP[GENERATION_PROFILE_NAME],
            },
            "indexing": {
                "embedding_profile": index_state.embedding_profile,
            },
        },
    )


@app.get("/summary", response_model=SummaryResponse)
def summary(question: str | None = None, limit: int = 5) -> SummaryResponse:
    metrics_state = metrics()
    sample = stats()
    source_count = len({path for path in sample["sample_paths"] if path})
    grouped_sources: list[dict[str, Any]] | None = None
    best_source: dict[str, Any] | None = None
    summary_notes = [
        "Grouped context is available through the grounded answer path.",
        "Hybrid retrieval, incremental indexing, and profile selection are active.",
    ]

    if question:
        matches = retrieve_chunks(
            query=question,
            limit=max(1, min(limit, 10)),
            debug=False,
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for match in matches:
            grouped.setdefault(str(match["path"]), []).append(match)
        grouped_sources = []
        for path, source_chunks in grouped.items():
            ordered_chunks = sorted(source_chunks, key=lambda item: (item["distance"], item["line_start"]))
            digest = " | ".join(
                chunk.get("snippet", "").strip()
                for chunk in ordered_chunks[:2]
                if chunk.get("snippet", "").strip()
            )
            average_distance = sum(chunk["distance"] for chunk in ordered_chunks) / max(1, len(ordered_chunks))
            if average_distance <= 0.25:
                confidence = "high"
                confidence_reason = f"tight cluster around {average_distance:.2f} average distance"
            elif average_distance <= 0.5:
                confidence = "medium"
                confidence_reason = f"moderate spread around {average_distance:.2f} average distance"
            else:
                confidence = "low"
                confidence_reason = f"broader spread around {average_distance:.2f} average distance"
            grouped_sources.append(
                {
                    "path": path,
                    "chunk_count": len(source_chunks),
                    "top_span": {
                        "line_start": ordered_chunks[0]["line_start"],
                        "line_end": ordered_chunks[0]["line_end"],
                        "snippet": ordered_chunks[0].get("snippet", ""),
                        "distance": ordered_chunks[0]["distance"],
                    } if ordered_chunks else None,
                    "digest": digest,
                    "confidence": confidence,
                    "confidence_reason": confidence_reason,
                    "note": (
                        f"Most relevant context: {digest}; {confidence_reason}"
                        if digest
                        else f"Most relevant context: none captured; {confidence_reason}"
                    ),
                    "chunks": [
                        {
                            "line_start": chunk["line_start"],
                            "line_end": chunk["line_end"],
                            "snippet": chunk.get("snippet", ""),
                            "distance": chunk["distance"],
                        }
                        for chunk in ordered_chunks
                    ],
                }
            )
        best_source = sorted(
            grouped_sources,
            key=lambda source: (
                {"high": 0, "medium": 1, "low": 2}[source["confidence"]],
                source["top_span"]["distance"] if source["top_span"] else 1.0,
                -source["chunk_count"],
            ),
        )[0] if grouped_sources else None
        confidence_mix = {level: sum(1 for source in grouped_sources if source["confidence"] == level) for level in ("high", "medium", "low")}
        summary_notes = [
            f"Retrieved {len(matches)} chunks across {len(grouped_sources)} grouped sources for the query.",
            f"Confidence mix: {confidence_mix['high']} high, {confidence_mix['medium']} medium, {confidence_mix['low']} low.",
            "Chunks are grouped by source so cross-document reasoning stays coherent.",
        ]

    best_source_reason = None
    if question and best_source is None:
        sample_paths = [path for path in sample["sample_paths"] if path]
        best_source = {
            "path": sample_paths[0] if sample_paths else collection.name,
            "chunk_count": 0,
            "top_span": None,
            "digest": "",
            "confidence": "low",
            "confidence_reason": "no retrieval matches were returned; using sampled source",
            "note": "Most relevant context: none captured; no retrieval matches were returned",
            "chunks": [],
        }
        best_source_reason = best_source["confidence_reason"]
    elif best_source is not None:
        best_source_reason = (
            f"selected as {best_source['confidence']} confidence with top span distance "
            f"{best_source['top_span']['distance']:.2f} and {best_source['chunk_count']} chunks"
            if best_source["top_span"]
            else f"selected as {best_source['confidence']} confidence fallback with {best_source['chunk_count']} chunks"
        )

    return SummaryResponse(
        status="ok",
        collection=collection.name,
        ready=metrics_state.ready,
        sources=source_count if grouped_sources is None else len(grouped_sources),
        chunks=metrics_state.chunks,
        question=question,
        best_source=best_source,
        best_source_reason=best_source_reason,
        grouped_sources=grouped_sources,
        notes=summary_notes,
        retrieval_modes=metrics_state.retrieval_modes,
        profiles=metrics_state.profiles,
    )


@app.get("/platform/summary", response_model=PlatformSummaryResponse)
def platform_summary() -> PlatformSummaryResponse:
    return PlatformSummaryResponse(
        status="ok",
        ready=True,
        sections=["ai_platform", "ai_services", "rag_api", "ingestion", "local_rag", "integrations"],
        ai_services=["local LLM service", "embedding service", "vector database", "RAG API"],
        notes=[
            "AI surfaces are available through the platform endpoints.",
            "AI services, RAG orchestration, and ingestion are ready as plans and compose artifacts.",
        ],
    )


@app.get("/index/status", response_model=IndexStatusResponse)
@app.get("/platform/status", response_model=PlatformStatusResponse)
def platform_status() -> PlatformStatusResponse:
    return PlatformStatusResponse(
        status="ok",
        sections=["ai_platform", "ai_services", "rag_api", "ingestion", "local_rag", "integrations"],
        ai_platform="available",
        ai_services="available",
        rag_api="available",
        ingestion="available",
        local_rag="available",
        integrations=["n8n", "MCP", "Skills"],
        notes=[
            "AI platform planning is available through the /platform endpoint.",
            "AI services and RAG orchestration are available as compose and plan artifacts.",
            "Ingestion, integrations, and local RAG are discoverable from the app layer.",
        ],
    )

def index_status() -> IndexStatusResponse:
    return IndexStatusResponse(
        **build_index_status(collection),
    )


@app.get("/stats")
def stats() -> dict[str, Any]:
    sample = collection.peek(limit=5)

    return {
        "collection": collection.name,
        "chunks": collection.count(),
        "sample_ids": sample.get("ids", []),
        "sample_paths": [
            metadata.get("path")
            for metadata in sample.get(
                "metadatas",
                [],
            )
            if metadata
        ],
    }


@app.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    return StatusResponse(
        status="ok",
        version=APP_VERSION,
        vector_store="chromadb",
        collection=collection.name,
        chunks=collection.count(),
        embedding_model=EMBEDDING_MODEL,
        embedding_model_fallbacks=EMBEDDING_MODEL_FALLBACKS,
        embedding_profile=EMBEDDING_PROFILE_NAME,
        generation_model=GENERATION_MODEL,
        generation_profile=GENERATION_PROFILE_NAME,
        generation_options=GENERATION_PROFILE_MAP[GENERATION_PROFILE_NAME],
        reranker_enabled=reranker.enabled,
        reranker_model=reranker.model_name,
        reranker_threads=reranker.threads,
        retrieval_modes=["vector", "lexical", "hybrid"],
        capabilities=[
            "document parsing",
            "chunking",
            "embeddings",
            "vector search",
            "metadata filtering",
            "grounded answers",
        ],
        roadmap_items=[
            "hybrid search",
            "cross-document reasoning",
            "citation ranking",
            "incremental updates",
            "multiple embedding models",
        ],
    )









