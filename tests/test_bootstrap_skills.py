from pathlib import Path

from bootstrap.manifests import infrastructure_manifest
from bootstrap.skills import build_skills_plan, render_skills_plan


def test_build_skills_plan_describes_local_capabilities() -> None:
    manifest = infrastructure_manifest()
    plan = build_skills_plan(manifest)

    assert plan.service == "Skills registry"
    assert plan.skills[0].name == "bootstrap-validation"
    assert plan.skills[1].category == "platform"
    assert "repeatable local procedures" in plan.packaging_notes
    assert "repository-backed manifests" in plan.discovery_notes


def test_render_skills_plan_returns_invocations() -> None:
    manifest = infrastructure_manifest()
    plan = render_skills_plan(manifest)

    assert plan["service"] == "Skills registry"
    assert plan["skills"][0]["invocation"] == "aisha skills run bootstrap-validation"
    assert "operator" in plan["skills"][3]["purpose"]


def test_bundle_writes_skills_registry() -> None:
    from bootstrap.bundle import write_bootstrap_bundle

    bundle_dir = Path("bootstrap") / "skills-bundle-test"
    bundle = write_bootstrap_bundle(infrastructure_manifest(), bundle_dir)

    assert bundle.skills_registry_path.exists()
    assert bundle.skills_path.exists()
    assert bundle.n8n_path.exists()
    assert bundle.mcp_path.exists()
