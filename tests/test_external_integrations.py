from bootstrap.external_integrations import build_external_integration_plan, render_external_integration_plan
from bootstrap.manifests import infrastructure_manifest


def test_external_integration_plan_includes_webhook_targets() -> None:
    plan = build_external_integration_plan(infrastructure_manifest())

    assert plan.systems[2] == "Slack"
    assert plan.webhook_targets[0].env_var == "SLACK_WEBHOOK_URL"
    assert plan.webhook_targets[1].example_export == "scripts/discord_alerts_n8n_export.json"
    assert plan.webhook_targets[2].transport == "bot sendMessage API"
    assert plan.setup_flow[0] == "choose the target platform"


def test_render_external_integration_plan_returns_webhook_metadata() -> None:
    plan = render_external_integration_plan(infrastructure_manifest())

    assert plan["webhook_targets"][0]["name"] == "Slack"
    assert plan["webhook_targets"][2]["env_var"] == "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID"
    assert "consistent webhook patterns" in plan["notes"]


def test_dispatcher_script_exists_and_formats_shared_payloads() -> None:
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    script_path = Path('scripts/mission_control_webhook_dispatcher.py')
    assert script_path.exists()

    spec = spec_from_file_location('mission_control_webhook_dispatcher', script_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    payload = module.build_approval_payload({'id': 'abc', 'title': 'Upgrade', 'summary': 'Roll forward', 'risk': 'high', 'requested_by': 'infra-agent'})
    assert payload['approval_id'] == 'abc'
    assert payload['kind'] == 'approval_requested'
    assert payload['dashboard_url']


def test_seed_script_exists_and_references_demo_approval() -> None:
    from pathlib import Path

    script = Path('scripts/seed_mission_control_demo.py')
    body = script.read_text(encoding='utf-8')

    assert script.exists()
    assert 'demo-approval-traefik-upgrade' in body
    assert 'insert_approval' in body
    assert 'approval_requested' in body
