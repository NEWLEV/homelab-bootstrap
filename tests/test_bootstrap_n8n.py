from bootstrap.manifests import infrastructure_manifest
from bootstrap.n8n import build_n8n_plan, render_n8n_plan


def test_build_n8n_plan_describes_workflows_and_triggers() -> None:
    manifest = infrastructure_manifest()
    plan = build_n8n_plan(manifest)

    assert plan.service == "n8n"
    assert "nightly backups" in plan.workflows
    assert "Slack approval routing" in plan.workflows
    assert "schedule" in plan.triggers
    assert "Slack incoming webhook" in plan.notification_targets
    assert "scripts/slack_alerts_n8n_export.json" in plan.example_exports
    assert "bounded attempts" in plan.retry_strategy
    assert "approval" in plan.approval_strategy


def test_render_n8n_plan_returns_json_friendly_output() -> None:
    manifest = infrastructure_manifest()
    plan = render_n8n_plan(manifest)

    assert plan["service"] == "n8n"
    assert "manual approval" in plan["triggers"]
    assert plan["notification_targets"][0] == "Slack incoming webhook"
    assert "scripts/mission_control_n8n_export.json" in plan["example_exports"]
    assert "externally visible" in plan["approval_strategy"]
