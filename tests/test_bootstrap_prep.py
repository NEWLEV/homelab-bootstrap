from pathlib import Path

from bootstrap.infrastructure import ManifestValidationError
from bootstrap.prep import main, prepare_bootstrap


def test_prepare_bootstrap_writes_artifacts() -> None:
    manifest = Path("bootstrap") / "infrastructure.yaml"
    compose_output = Path("bootstrap") / "compose.prep-test.yaml"
    report_output = Path("bootstrap") / "bootstrap.prep-test.json"
    bundle_dir = Path("bootstrap") / "prep-bundle-test"

    result = prepare_bootstrap(
        manifest,
        compose_output=compose_output,
        report_output=report_output,
        bundle_dir=bundle_dir,
    )

    assert result.succeeded is True
    assert result.validate_exit_code == 0
    assert result.compose_exit_code == 0
    assert result.report_exit_code == 0
    assert result.bundle_exit_code == 0
    assert compose_output.exists()
    assert report_output.exists()
    assert bundle_dir.exists()
    assert (bundle_dir / "compose.generated.yaml").exists()
    assert (bundle_dir / "bootstrap.report.json").exists()
    assert (bundle_dir / "dependency.graph.json").exists()
    assert (bundle_dir / "backup.plan.json").exists()
    assert (bundle_dir / "storage-network.plan.json").exists()
    assert (bundle_dir / "monitoring.plan.json").exists()
    assert "x-aisha-hooks:" in compose_output.read_text(encoding="utf-8")
    assert '"manifest": "infrastructure"' in report_output.read_text(encoding="utf-8")


def test_prep_main_supports_flags() -> None:
    compose_output = Path("bootstrap") / "compose.prep-flags.yaml"
    report_output = Path("bootstrap") / "bootstrap.prep-flags.json"
    bundle_dir = Path("bootstrap") / "prep-bundle-flags"
    exit_code = main([
        "--manifest",
        str(Path("bootstrap") / "infrastructure.yaml"),
        "--compose-output",
        str(compose_output),
        "--report-output",
        str(report_output),
        "--bundle-dir",
        str(bundle_dir),
    ])

    assert exit_code == 0
    assert compose_output.exists()
    assert report_output.exists()
    assert bundle_dir.exists()


def test_prep_main_defaults_to_repo_paths() -> None:
    compose_output = Path("bootstrap") / "compose.prep-default.yaml"
    report_output = Path("bootstrap") / "bootstrap.prep-default.json"
    bundle_dir = Path("bootstrap") / "prep-bundle-default"

    exit_code = main([
        str(Path("bootstrap") / "infrastructure.yaml"),
        str(compose_output),
        str(report_output),
        str(bundle_dir),
    ])

    assert exit_code == 0
    assert compose_output.exists()
    assert report_output.exists()
    assert bundle_dir.exists()


def test_prepare_bootstrap_rejects_invalid_manifest() -> None:
    manifest = Path("bootstrap") / "broken.prep-test.yaml"
    manifest.write_text("name: broken\nservices: []\nvolumes: []\nnetworks: []\n", encoding="utf-8")

    try:
        prepare_bootstrap(
            manifest,
            compose_output=Path("bootstrap") / "broken.compose.yaml",
            report_output=Path("bootstrap") / "broken.report.json",
            bundle_dir=Path("bootstrap") / "broken.bundle",
        )
    except ManifestValidationError as exc:
        assert "manifest schema validation failed" in str(exc)
    else:
        raise AssertionError("invalid manifests must fail before prep artifacts are written")



def test_prepare_bootstrap_compose_contains_mission_control_build_context() -> None:
    compose_output = Path('bootstrap') / 'compose.prep-mission-control.yaml'
    report_output = Path('bootstrap') / 'bootstrap.prep-mission-control.json'
    bundle_dir = Path('bootstrap') / 'prep-bundle-mission-control'

    result = prepare_bootstrap(
        Path('bootstrap') / 'infrastructure.yaml',
        compose_output=compose_output,
        report_output=report_output,
        bundle_dir=bundle_dir,
    )

    assert result.succeeded is True
    contents = compose_output.read_text(encoding='utf-8')
    assert 'mission-control:' in contents
    assert 'context: homelab-bootstrap/services/mission-control' in contents
    assert 'dockerfile: Dockerfile' in contents
