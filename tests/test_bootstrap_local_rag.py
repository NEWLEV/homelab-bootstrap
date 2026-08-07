from bootstrap.manifests import infrastructure_manifest
from bootstrap.local_rag import build_local_rag_plan, render_local_rag_plan


def test_build_local_rag_plan_lists_runtime_components() -> None:
    manifest = infrastructure_manifest()
    plan = build_local_rag_plan(manifest)

    assert "vector database" in plan.components
    assert "grounded answers" in plan.capabilities
    assert "hybrid search" in plan.roadmap_items
    assert plan.storage_plan["backend"] == "persistent vector store"
    assert plan.storage_plan["location"] == "/srv/data/services/vector-database"


def test_render_local_rag_plan_returns_deployment_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_local_rag_plan(manifest)

    assert "retrieval API" in plan["components"]
    assert "shared infrastructure layer" in plan["deployment_notes"]
    assert "restore the vector store" in plan["storage_plan"]["restore"]
