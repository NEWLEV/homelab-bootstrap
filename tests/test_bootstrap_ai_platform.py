from pathlib import Path

from bootstrap.agent_platform import build_agent_platform_plan, render_agent_platform_plan
from bootstrap.ai_platform import build_ai_platform_plan, render_ai_platform_plan
from bootstrap.ai_services import build_ai_services_plan, render_ai_services_compose_yaml, render_ai_services_plan
from bootstrap.cli import main
from bootstrap.ingestion import build_ingestion_plan, render_ingestion_plan
from bootstrap.integrations import build_integration_registry, render_integration_registry
from bootstrap.manifests import infrastructure_manifest
from bootstrap.memory import build_memory_plan, render_memory_plan
from bootstrap.models import build_model_layer_plan, render_model_layer_plan
from bootstrap.rag_api import build_rag_api_plan, render_rag_api_plan


def test_build_ai_platform_plan_lists_core_services() -> None:
    manifest = infrastructure_manifest()
    plan = build_ai_platform_plan(manifest)

    assert "OpenClaw runtime" in plan.services
    assert "vector database" in plan.storage_services
    assert "retrieve context" in plan.workflow_steps
    assert "n8n for durable orchestration" in plan.integration_layers
    assert plan.model_layer["services"][0]["name"] == "local LLM service"
    assert plan.service_layer["deployment_order"] == ["local LLM service", "embedding service", "vector database", "RAG API"]
    assert plan.rag_api["steps"][0]["name"] == "retrieve"
    assert plan.ingestion["steps"][0]["name"] == "discover"


def test_render_ai_platform_plan_returns_deployment_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_ai_platform_plan(manifest)

    assert plan["model_services"] == ["local LLM service", "embedding service"]
    assert "shared infrastructure layer" in plan["deployment_notes"]
    assert "integration_layers" in plan
    assert "MCP for structured tool access" in plan["integration_layers"]
    assert plan["model_layer"]["services"][1]["storage"] == "embedding model weights stored on local persistent disk"
    assert plan["service_layer"]["boundary_notes"].startswith("deploy AI services")
    assert plan["rag_api"]["steps"][2]["depends_on"] == ["rerank", "local LLM service"]
    assert plan["ingestion"]["steps"][4]["name"] == "index"


def test_build_integration_registry_orders_platform_tools() -> None:
    manifest = infrastructure_manifest()
    registry = build_integration_registry(manifest)

    assert registry.entries[0].name == "n8n"
    assert registry.entries[1].name == "MCP"
    assert registry.entries[2].name == "Skills"
    assert registry.entries[0].priority < registry.entries[1].priority < registry.entries[2].priority


def test_render_integration_registry_returns_entries() -> None:
    manifest = infrastructure_manifest()
    registry = render_integration_registry(manifest)

    assert registry["entries"][0]["name"] == "n8n"
    assert registry["entries"][1]["layer"] == "tooling"
    assert "structured tool access" in registry["entries"][1]["purpose"]


def test_build_model_layer_plan_describes_local_services() -> None:
    manifest = infrastructure_manifest()
    plan = build_model_layer_plan(manifest)

    assert plan.services[0].name == "local LLM service"
    assert plan.services[1].role == "vector generation"
    assert "local-only access" in plan.deployment_notes


def test_render_model_layer_plan_returns_services() -> None:
    manifest = infrastructure_manifest()
    plan = render_model_layer_plan(manifest)

    assert plan["services"][0]["name"] == "local LLM service"
    assert plan["services"][1]["storage"] == "embedding model weights stored on local persistent disk"
    assert "typed bridge" not in plan["routing_notes"]


def test_build_ai_services_plan_describes_boundaries() -> None:
    manifest = infrastructure_manifest()
    plan = build_ai_services_plan(manifest)

    assert plan.deployment_order == ("local LLM service", "embedding service", "vector database", "RAG API")
    assert plan.services[2].depends_on == ("embedding service",)
    assert "private" in plan.boundary_notes


def test_render_ai_services_plan_returns_order() -> None:
    manifest = infrastructure_manifest()
    plan = render_ai_services_plan(manifest)

    assert plan["services"][0]["name"] == "local LLM service"
    assert plan["services"][3]["depends_on"] == ["local LLM service", "embedding service", "vector database"]


def test_render_ai_services_compose_yaml_contains_services() -> None:
    manifest = infrastructure_manifest()
    yaml_text = render_ai_services_compose_yaml(manifest)

    assert "name: aisha-ai-services" in yaml_text
    assert "local LLM service:" in yaml_text
    assert "vector-db-data" in yaml_text


def test_build_rag_api_plan_describes_retrieval_flow() -> None:
    manifest = infrastructure_manifest()
    plan = build_rag_api_plan(manifest)

    assert plan.service == "RAG API"
    assert plan.steps[0].name == "retrieve"
    assert plan.steps[2].depends_on == ("rerank", "local LLM service")
    assert "grounded answer" in plan.outputs[0]


def test_render_rag_api_plan_returns_flow() -> None:
    manifest = infrastructure_manifest()
    plan = render_rag_api_plan(manifest)

    assert plan["service"] == "RAG API"
    assert plan["steps"][1]["purpose"] == "rank retrieved chunks for answer quality"
    assert "external access is explicitly approved" in plan["boundary_notes"]


def test_build_ingestion_plan_describes_indexing_flow() -> None:
    manifest = infrastructure_manifest()
    plan = build_ingestion_plan(manifest)

    assert plan.service == "ingestion and indexing"
    assert plan.steps[0].name == "discover"
    assert plan.steps[3].depends_on == ("chunk", "embedding service")
    assert "retry parse" in plan.retry_notes


def test_render_ingestion_plan_returns_flow() -> None:
    manifest = infrastructure_manifest()
    plan = render_ingestion_plan(manifest)

    assert plan["service"] == "ingestion and indexing"
    assert plan["steps"][4]["name"] == "index"
    assert "private vector store" in plan["boundary_notes"]


def test_cli_ingestion_prints_json(capsys) -> None:
    exit_code = main(["--ingestion"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"service": "ingestion and indexing"' in captured.out
    assert '"discover"' in captured.out


def test_bundle_writes_ai_services_plan() -> None:
    from bootstrap.bundle import write_bootstrap_bundle

    bundle_dir = Path("bootstrap") / "ai-services-bundle-test"
    bundle = write_bootstrap_bundle(infrastructure_manifest(), bundle_dir)

    assert bundle.ai_services_path.exists()
    assert bundle.ai_services_compose_path.exists()
    assert bundle.rag_api_path.exists()
    assert bundle.ingestion_path.exists()
    assert bundle.ai_platform_path.exists()
    assert bundle.local_rag_path.exists()


def test_build_agent_platform_plan_describes_planning_layers() -> None:
    manifest = infrastructure_manifest()
    plan = build_agent_platform_plan(manifest)

    assert plan.planners[0] == "task planner"
    assert plan.routers[1] == "model router"
    assert plan.execution_layers[-1] == "workflow execution"
    assert plan.memory_layers[0] == "short-term memory"


def test_render_agent_platform_plan_returns_workflow_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_agent_platform_plan(manifest)

    assert plan["planners"][2] == "policy planner"
    assert "repository-managed artifacts" in plan["workflow_notes"]


def test_build_memory_plan_describes_retrieval_strategy() -> None:
    manifest = infrastructure_manifest()
    plan = build_memory_plan(manifest)

    assert plan.memory_types[0] == "conversation"
    assert "repository-backed" in plan.storage
    assert "indexed search first" in plan.retrieval_notes


def test_render_memory_plan_returns_storage_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_memory_plan(manifest)

    assert plan["memory_types"][-1] == "documents"
    assert "revision history" in plan["retention_notes"]
