from bootstrap.manifests import infrastructure_manifest
from bootstrap.monitoring import build_monitoring_plan, render_monitoring_plan


def test_build_monitoring_plan_describes_targets_and_sources() -> None:
    manifest = infrastructure_manifest()
    plan = build_monitoring_plan(manifest)

    assert plan.service == "monitoring"
    assert "cpu" in plan.metric_targets
    assert "service availability" in plan.dashboard_expectations
    assert plan.alerting_targets == ("containers", "healthchecks", "backups")
    assert plan.log_sources == ("reverse-proxy", "monitoring", "backups")
    assert plan.hooks["scrape"] == ("metrics", "health", "logs")


def test_render_monitoring_plan_returns_collection_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_monitoring_plan(manifest)

    assert plan["service"] == "monitoring"
    assert plan["metric_targets"][0] == "cpu"
    assert "manual inspection" in plan["collection_notes"]
    assert plan["hooks"]["alert"] == ["containers", "healthchecks", "backups"]
