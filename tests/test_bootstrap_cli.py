from pathlib import Path

from bootstrap.bundle import write_bootstrap_bundle
from bootstrap.cli import main
from bootstrap.manifests import infrastructure_manifest


def test_cli_plan_outputs_json(capsys) -> None:
    exit_code = main(["--plan"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"storage"' in captured.out
    assert '"reverse-proxy"' in captured.out


def test_cli_graph_outputs_json(capsys) -> None:
    exit_code = main(["--graph"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"nodes"' in captured.out
    assert '"edges"' in captured.out
    assert '"monitoring"' in captured.out


def test_cli_storage_network_outputs_json(capsys) -> None:
    exit_code = main(["--storage-network"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"volume_paths"' in captured.out
    assert '"boundaries"' in captured.out


def test_cli_monitoring_outputs_json(capsys) -> None:
    exit_code = main(["--monitoring"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"metric_targets"' in captured.out
    assert '"collection_notes"' in captured.out


def test_cli_exposure_outputs_json(capsys) -> None:
    exit_code = main(["--exposure"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"public_entrypoint": "edge"' in captured.out
    assert '"access_policy"' in captured.out


def test_cli_dns_tls_outputs_json(capsys) -> None:
    exit_code = main(["--dns-tls"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"tls_strategy"' in captured.out
    assert '"certificate_source"' in captured.out


def test_cli_backup_plan_outputs_json(capsys) -> None:
    exit_code = main(["--backup-plan"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"schedule": "daily"' in captured.out
    assert '"restore_check"' in captured.out


def test_cli_readiness_outputs_json(capsys) -> None:
    exit_code = main(["--readiness"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"ready": true' in captured.out
    assert '"artifacts"' in captured.out


def test_cli_status_outputs_json(capsys) -> None:
    exit_code = main(["--status"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"ready": true' in captured.out
    assert '"paths"' in captured.out


def test_cli_ai_platform_outputs_json(capsys) -> None:
    exit_code = main(["--ai-platform"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"OpenClaw runtime"' in captured.out
    assert '"workflow_steps"' in captured.out


def test_cli_bundle_outputs_paths(capsys) -> None:
    bundle_dir = Path("bootstrap") / "bundle-test"

    exit_code = main(["--bundle", "--bundle-dir", str(bundle_dir)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"bundle_dir"' in captured.out
    assert bundle_dir.exists()
    assert (bundle_dir / "compose.generated.yaml").exists()
    assert (bundle_dir / "bootstrap.report.json").exists()
    assert (bundle_dir / "dependency.graph.json").exists()
    assert (bundle_dir / "backup.plan.json").exists()
    assert (bundle_dir / "storage-network.plan.json").exists()
    assert (bundle_dir / "monitoring.plan.json").exists()
    assert (bundle_dir / "exposure.plan.json").exists()
    assert (bundle_dir / "readiness.summary.json").exists()
    assert (bundle_dir / "dns-tls.plan.json").exists()
    assert (bundle_dir / "ai-platform.plan.json").exists()


def test_cli_run_outputs_summary(capsys) -> None:
    exit_code = main(["--run"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"phase_name": "infrastructure"' in captured.out
    assert '"storage"' in captured.out


def test_cli_prints_schema(capsys) -> None:
    exit_code = main(["--schema"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'Aisha Infrastructure Manifest' in captured.out
    assert '"services"' in captured.out


def test_cli_validates_manifest(capsys) -> None:
    exit_code = main(["--validate"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "valid"' in captured.out
    assert '"service_order"' in captured.out


def test_cli_prints_compose_yaml(capsys) -> None:
    exit_code = main(["--compose"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "services:" in captured.out
    assert "reverse-proxy:" in captured.out
    assert "traefik:v3.1" in captured.out
    assert "x-aisha-hooks:" in captured.out
    assert "targets:" in captured.out


def test_cli_writes_compose_yaml(capsys) -> None:
    output = Path("bootstrap") / "compose.write-test.yaml"

    exit_code = main(["--write-compose", "--output", str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == str(output)
    assert output.exists()
    contents = output.read_text(encoding="utf-8")
    assert "services:" in contents
    assert "x-aisha-hooks:" in contents


def test_cli_prints_bootstrap_report(capsys) -> None:
    exit_code = main(["--report"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"manifest": "infrastructure"' in captured.out
    assert '"compose_output": "bootstrap/compose.generated.yaml"' in captured.out
    assert '"phase_names"' in captured.out
    assert '"hooks"' in captured.out
    assert '"backup_plan"' in captured.out
    assert '"readiness"' in captured.out


def test_cli_writes_bootstrap_report(capsys) -> None:
    output = Path("bootstrap") / "bootstrap.write-test.json"

    exit_code = main(["--write-report", "--report-output", str(output)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == str(output)
    assert output.exists()
    contents = output.read_text(encoding="utf-8")
    assert '"manifest": "infrastructure"' in contents
    assert '"compose_output": "bootstrap/compose.generated.yaml"' in contents
    assert '"hooks"' in contents
    assert '"backup_plan"' in contents
    assert '"readiness"' in contents


def test_cli_rejects_invalid_manifest(capsys) -> None:
    manifest = Path("bootstrap") / "broken.cli-test.yaml"
    manifest.write_text("name: broken\nservices: []\nvolumes: []\nnetworks: []\n", encoding="utf-8")

    exit_code = main([str(manifest), "--plan"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "manifest schema validation failed" in captured.err
    assert captured.out == ""


def test_cli_requires_mode(capsys) -> None:
    try:
        main([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("the CLI must require a mode")



def test_cli_compose_includes_mission_control_build_context(capsys) -> None:
    exit_code = main(["--compose"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'mission-control:' in captured.out
    assert 'build:' in captured.out
    assert 'context: homelab-bootstrap/services/mission-control' in captured.out
    assert 'dockerfile: Dockerfile' in captured.out
