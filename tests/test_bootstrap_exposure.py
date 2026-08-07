from bootstrap.manifests import infrastructure_manifest
from bootstrap.exposure import build_exposure_plan, render_exposure_plan


def test_build_exposure_plan_identifies_public_and_private_services() -> None:
    manifest = infrastructure_manifest()
    plan = build_exposure_plan(manifest)

    assert plan.service == "reverse-proxy"
    assert plan.public_entrypoint == "edge"
    assert plan.tls_terminator == "traefik"
    assert plan.exposed_services == ("reverse-proxy",)
    assert "monitoring" in plan.internal_services
    assert "backups" in plan.internal_services
    assert plan.access_policy["public"] == ("reverse-proxy",)


def test_render_exposure_plan_returns_access_policy() -> None:
    manifest = infrastructure_manifest()
    plan = render_exposure_plan(manifest)

    assert plan["service"] == "reverse-proxy"
    assert plan["access_policy"]["public"] == ["reverse-proxy"]
    assert "private" in plan["access_policy"]
    assert "internal networks" in plan["boundary_notes"]
