from pathlib import Path

from bootstrap.cli import main
from bootstrap.infrastructure import ManifestValidationError, load_manifest, load_manifest_from_file, validate_manifest_schema


def test_schema_validation_rejects_unknown_fields() -> None:
    try:
        validate_manifest_schema(
            {
                "name": "infrastructure",
                "services": [
                    {"name": "monitoring", "image": "prom/prometheus:v2", "unexpected": True}
                ],
                "volumes": [],
                "networks": [],
            }
        )
    except ManifestValidationError as exc:
        assert "manifest schema validation failed" in str(exc)
    else:
        raise AssertionError("schema validation must reject unknown fields")


def test_load_manifest_from_file_round_trips_repo_manifest() -> None:
    manifest_path = Path("bootstrap") / "infrastructure.yaml"
    manifest = load_manifest_from_file(manifest_path)

    assert manifest.name == "infrastructure"
    assert [service.name for service in manifest.services] == [
        "reverse-proxy",
        "monitoring",
        "mission-control",
        "backups",
    ]
    assert manifest.volumes == ("prometheus-data", "mission-control-data", "backup-data")
    assert manifest.networks == ("edge", "internal")


def test_mission_control_event_and_approval_schemas_are_strict() -> None:
    import json
    from jsonschema import validate, ValidationError

    event_schema = json.loads(Path('schemas/mission_control/agent-event.schema.json').read_text(encoding='utf-8'))
    approval_schema = json.loads(Path('schemas/mission_control/approval.schema.json').read_text(encoding='utf-8'))

    validate(instance={'agent': 'ops-agent', 'kind': 'task_started', 'title': 'boot'}, schema=event_schema)
    validate(instance={'requested_by': 'infra-agent', 'title': 'upgrade'}, schema=approval_schema)

    try:
        validate(instance={'agent': 'ops-agent', 'kind': 'task_started', 'title': 'boot', 'unexpected': True}, schema=event_schema)
    except ValidationError:
        pass
    else:
        raise AssertionError('event schema must reject extra properties')
