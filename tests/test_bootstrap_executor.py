from __future__ import annotations

from pathlib import Path

from bootstrap.executor import build_phase_payload, infrastructure_phase_names, run_infrastructure_phases
from bootstrap.infrastructure import ManifestValidationError, load_manifest_from_file
from bootstrap.manifests import infrastructure_manifest


def test_infrastructure_phase_names_are_explicit() -> None:
    assert infrastructure_phase_names() == (
        "storage",
        "networking",
        "monitoring",
        "backups",
    )


def test_run_infrastructure_phases_executes_in_order() -> None:
    manifest = infrastructure_manifest()
    calls: list[str] = []

    summary = run_infrastructure_phases(
        manifest,
        phase_handler=lambda phase_name, payload: calls.append(phase_name),
    )

    assert calls == ["storage", "networking", "monitoring", "backups"]
    assert summary.phase_name == "infrastructure"
    assert [result.name for result in summary.results] == calls
    assert all(result.status == "completed" for result in summary.results)
    assert summary.total_duration_seconds >= 0


def test_build_phase_payload_includes_plans() -> None:
    manifest = infrastructure_manifest()
    payload = build_phase_payload(manifest)

    assert payload["compose"]["services"]["reverse-proxy"]["ports"] == ["80:80", "443:443"]
    assert payload["storage"].volumes == ("prometheus-data", "backup-data")
    assert payload["networking"].networks == ("edge", "internal")
    assert payload["service_order"] == ("reverse-proxy", "monitoring", "backups")
    assert payload["phases"]["storage"] == "Provision and validate persistent storage."


def test_load_manifest_from_file_round_trips_repo_manifest() -> None:
    manifest_path = Path("bootstrap") / "infrastructure.yaml"
    manifest = load_manifest_from_file(manifest_path)

    assert manifest.name == "infrastructure"
    assert [service.name for service in manifest.services] == [
        "reverse-proxy",
        "monitoring",
        "backups",
    ]
    assert manifest.volumes == ("prometheus-data", "backup-data")
    assert manifest.networks == ("edge", "internal")


def test_run_infrastructure_phases_propagates_validation_errors() -> None:
    manifest = infrastructure_manifest()

    try:
        run_infrastructure_phases(
            manifest,
            phase_handler=lambda phase_name, payload: (_ for _ in ()).throw(
                ManifestValidationError("boom")
            ) if phase_name == "monitoring" else None,
        )
    except ManifestValidationError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("phase validation errors must stop execution")
