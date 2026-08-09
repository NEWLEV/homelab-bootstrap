from __future__ import annotations

from pathlib import Path


def test_dashboard_bootstrap_artifacts_exist() -> None:
    service_dir = Path(r"C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/dashboard")

    assert (service_dir / "README.md").exists()
    assert (service_dir / "scripts" / "install-dashboard-service.sh").exists()
    assert (service_dir / "scripts" / "run-dashboard.sh").exists()
    assert (service_dir / "systemd" / "aisha-dashboard.service").exists()

    installer = (service_dir / "scripts" / "install-dashboard-service.sh").read_text(encoding="utf-8")
    unit = (service_dir / "systemd" / "aisha-dashboard.service").read_text(encoding="utf-8")

    assert "--host 0.0.0.0 --port 8000" in installer
    assert "--host 0.0.0.0 --port 8000" in unit



def test_mission_control_bootstrap_artifacts_exist() -> None:
    service_dir = Path(r'C:/Users/ZBook/Documents/Aisha/homelab-bootstrap/services/mission-control')

    assert (service_dir / 'README.md').exists()
    assert (service_dir / 'Dockerfile').exists()
    assert (service_dir / 'scripts' / 'run-mission-control.sh').exists()
    assert (service_dir / 'systemd' / 'aisha-mission-control.service').exists()

    installer = (service_dir / 'scripts' / 'install-mission-control-service.sh').read_text(encoding='utf-8')
    unit = (service_dir / 'systemd' / 'aisha-mission-control.service').read_text(encoding='utf-8')
    launcher = (service_dir / 'scripts' / 'run-mission-control.sh').read_text(encoding='utf-8')

    assert 'MISSION_CONTROL_PORT=8020' in unit
    assert 'ExecStart=%h/.venvs/aisha/bin/python -m mission_control' in unit
    assert 'ExecStart=%h/.venvs/aisha/bin/python -m mission_control' in installer
    assert 'AISHA_PYTHON' in launcher
    assert 'exec "$PYTHON_BIN" -m mission_control' in launcher


def test_openclaw_runtime_installer_exists() -> None:
    repo_root = Path(r"C:/Users/ZBook/Documents/Aisha")
    installer = repo_root / "scripts" / "install-openclaw-runtime"

    assert installer.exists()

    contents = installer.read_text(encoding="utf-8")

    assert "OPENCLAW_ENV_FILE" in contents
    assert 'OPENCLAW_ROOT="${OPENCLAW_ROOT:-/srv/data/services/openclaw}"' in contents
    assert 'OPENCLAW_ENV_FILE="${OPENCLAW_ENV_FILE:-$OPENCLAW_ROOT/secrets.env}"' in contents
    assert "/srv/data/services/local-rag/secrets/api-token" in contents
    assert "18790/aisha/api/health" in contents

def test_openclaw_ui_resolves_parent_origin() -> None:
    ui = Path(r"C:/Users/ZBook/Documents/Aisha/services/openclaw/ui/app.js")

    contents = ui.read_text(encoding="utf-8")

    assert "document.referrer" in contents
    assert "let parentOrigin = initialParentOrigin;" in contents
    assert "window.parent.postMessage(message, targetOrigin);" in contents
    assert "parentOrigin = event.origin;" in contents

def test_openclaw_ui_generates_message_ids_without_randomuuid() -> None:
    ui = Path(r"C:/Users/ZBook/Documents/Aisha/services/openclaw/ui/app.js")

    contents = ui.read_text(encoding="utf-8")

    assert "function createClientMessageId()" in contents
    assert "window.crypto.randomUUID" in contents
    assert "window.crypto.getRandomValues" in contents
    assert "fallback-" in contents
    assert "sendQuestion(question, createClientMessageId());" in contents


def test_integration_webhook_artifacts_and_docs_exist() -> None:
    repo_root = Path(r"C:/Users/ZBook/Documents/Aisha")

    slack_export = repo_root / "scripts" / "slack_alerts_n8n_export.json"
    discord_export = repo_root / "scripts" / "discord_alerts_n8n_export.json"
    telegram_export = repo_root / "scripts" / "telegram_alerts_n8n_export.json"
    sample_config = repo_root / "scripts" / "integration_webhooks.sample.json"
    dispatcher_script = repo_root / "scripts" / "mission_control_webhook_dispatcher.py"
    seed_script = repo_root / "scripts" / "seed_mission_control_demo.py"
    mission_control_doc = repo_root / "MISSION_CONTROL.md"
    services_doc = repo_root / "docs" / "services.md"

    assert slack_export.exists()
    assert discord_export.exists()
    assert telegram_export.exists()
    assert sample_config.exists()
    assert dispatcher_script.exists()
    assert seed_script.exists()

    slack_body = slack_export.read_text(encoding="utf-8")
    discord_body = discord_export.read_text(encoding="utf-8")
    telegram_body = telegram_export.read_text(encoding="utf-8")
    sample_body = sample_config.read_text(encoding="utf-8")
    dispatcher_body = dispatcher_script.read_text(encoding="utf-8")
    seed_body = seed_script.read_text(encoding="utf-8")
    mission_control_body = mission_control_doc.read_text(encoding="utf-8")
    services_body = services_doc.read_text(encoding="utf-8")

    assert "SLACK_WEBHOOK_URL" in slack_body
    assert "DISCORD_WEBHOOK_URL" in discord_body
    assert "TELEGRAM_BOT_TOKEN" in telegram_body
    assert "integration webhook check" in sample_body.lower()
    assert "SLACK_ALERT_WEBHOOK_URL" in dispatcher_body
    assert "DISCORD_ALERT_WEBHOOK_URL" in dispatcher_body
    assert "TELEGRAM_ALERT_WEBHOOK_URL" in dispatcher_body
    assert "discord_alerts_n8n_export.json" in mission_control_body
    assert "seed_mission_control_demo.py" in mission_control_body
    assert "Integration webhooks" in services_body
    assert "seed_mission_control_demo.py" in services_body
    assert "pending approval" in seed_body

