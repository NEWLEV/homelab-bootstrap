from bootstrap.backup import build_backup_plan, render_backup_plan
from bootstrap.manifests import infrastructure_manifest


def test_build_backup_plan_describes_retention_and_restore() -> None:
    manifest = infrastructure_manifest()
    plan = build_backup_plan(manifest)

    assert plan.service == "backups"
    assert plan.volume_names == ("prometheus-data", "backup-data")
    assert plan.schedule == "daily"
    assert "weekly" in plan.retention_policy
    assert "verification volume" in plan.restore_check
    assert plan.hooks["restore"] == "isolated verification restore"


def test_render_backup_plan_includes_targets() -> None:
    manifest = infrastructure_manifest()
    plan = render_backup_plan(manifest)

    assert plan["service"] == "backups"
    assert plan["volume_names"] == ["prometheus-data", "backup-data"]
    assert plan["targets"][0]["path"] == "/srv/data/services/prometheus-data"
    assert plan["hooks"]["schedule"] == "daily snapshot rotation"
