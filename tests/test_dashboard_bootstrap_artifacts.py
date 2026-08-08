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
    assert 'ExecStart=/usr/bin/env bash homelab-bootstrap/services/mission-control/scripts/run-mission-control.sh' in unit
    assert 'ExecStart=/usr/bin/env bash homelab-bootstrap/services/mission-control/scripts/run-mission-control.sh' in installer
    assert 'python -m mission_control' in launcher
