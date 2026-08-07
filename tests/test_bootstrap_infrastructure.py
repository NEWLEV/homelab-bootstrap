from pathlib import Path

from bootstrap.infrastructure import ManifestValidationError, load_manifest, load_manifest_from_file, validate_manifest_schema


def test_load_manifest_rejects_duplicates() -> None:
    try:
        load_manifest(
            {
                "name": "infrastructure",
                "services": [
                    {"name": "monitoring", "image": "prom/prometheus:v2"},
                    {"name": "monitoring", "image": "prom/prometheus:v2"},
                ],
                "volumes": [],
                "networks": [],
            }
        )
    except ManifestValidationError as exc:
        assert "duplicate service declaration" in str(exc)
    else:
        raise AssertionError("duplicate services must fail")


def test_load_manifest_rejects_missing_dependencies() -> None:
    try:
        load_manifest(
            {
                "name": "infrastructure",
                "services": [
                    {
                        "name": "monitoring",
                        "image": "prom/prometheus:v2",
                        "depends_on": ["reverse-proxy"],
                    }
                ],
                "volumes": [],
                "networks": [],
            }
        )
    except ManifestValidationError as exc:
        assert "unknown services" in str(exc)
    else:
        raise AssertionError("missing dependencies must fail")


def test_load_manifest_rejects_unknown_volume_reference() -> None:
    try:
        load_manifest(
            {
                "name": "infrastructure",
                "services": [
                    {
                        "name": "monitoring",
                        "image": "prom/prometheus:v2",
                        "volumes": ["prometheus-data"],
                    }
                ],
                "volumes": ["backup-data"],
                "networks": [],
            }
        )
    except ManifestValidationError as exc:
        assert "unknown volumes" in str(exc)
    else:
        raise AssertionError("unknown volume references must fail")


def test_load_manifest_rejects_unknown_network_reference() -> None:
    try:
        load_manifest(
            {
                "name": "infrastructure",
                "services": [
                    {
                        "name": "reverse-proxy",
                        "image": "traefik:v3.1",
                        "networks": ["edge"],
                    }
                ],
                "volumes": [],
                "networks": ["internal"],
            }
        )
    except ManifestValidationError as exc:
        assert "unknown networks" in str(exc)
    else:
        raise AssertionError("unknown network references must fail")



def test_load_manifest_includes_mission_control_service() -> None:
    manifest = load_manifest_from_file(Path('bootstrap') / 'infrastructure.yaml')

    service_names = [service.name for service in manifest.services]

    assert service_names == ['reverse-proxy', 'monitoring', 'mission-control', 'backups']
    mission_control = manifest.services[2]
    assert mission_control.command == 'python -m mission_control'
    assert mission_control.depends_on == ('reverse-proxy', 'monitoring')
