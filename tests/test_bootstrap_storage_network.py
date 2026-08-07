from bootstrap.manifests import infrastructure_manifest
from bootstrap.storage_network import build_storage_network_plan, render_storage_network_plan


def test_build_storage_network_plan_splits_storage_and_networking() -> None:
    manifest = infrastructure_manifest()
    plan = build_storage_network_plan(manifest)

    assert plan.storage["root"] == "/srv/data/services"
    assert plan.storage["volume_paths"]["prometheus-data"] == "/srv/data/services/prometheus-data"
    assert plan.networking["reverse_proxy_network"] == "edge"
    assert plan.networking["boundaries"]["public"] == ["edge"]
    assert plan.networking["boundaries"]["private"] == ["internal"]


def test_render_storage_network_plan_returns_both_sections() -> None:
    manifest = infrastructure_manifest()
    plan = render_storage_network_plan(manifest)

    assert "storage" in plan
    assert "networking" in plan
    assert plan["storage"]["volumes"] == ["prometheus-data", "backup-data"]


def test_build_storage_network_plan_rejects_missing_reverse_proxy_network() -> None:
    from bootstrap.infrastructure import InfrastructureManifest, ServiceDeclaration, ManifestValidationError
    from bootstrap.storage_network import build_storage_network_plan

    manifest = InfrastructureManifest(
        name="infrastructure",
        services=(
            ServiceDeclaration(name="monitoring", image="prom/prometheus:v2"),
        ),
        volumes=("prometheus-data",),
        networks=("internal",),
    )

    try:
        build_storage_network_plan(manifest)
    except ManifestValidationError as exc:
        assert "reverse proxy network" in str(exc)
    else:
        raise AssertionError("missing reverse proxy network must fail")
