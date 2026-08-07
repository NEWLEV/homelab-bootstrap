from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml


SCHEMA_PATH = Path(__file__).with_name("infrastructure.schema.json")


@dataclass(frozen=True)
class BuildDeclaration:
    context: str
    dockerfile: str = "Dockerfile"


@dataclass(frozen=True)
class ServiceDeclaration:
    name: str
    image: str | None = None
    build: BuildDeclaration | None = None
    depends_on: tuple[str, ...] = ()
    volumes: tuple[str, ...] = ()
    networks: tuple[str, ...] = ()
    command: str | None = None
    entrypoint: str | None = None
    healthcheck: str | None = None
    ports: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class InfrastructureManifest:
    name: str
    services: tuple[ServiceDeclaration, ...] = field(default_factory=tuple)
    volumes: tuple[str, ...] = field(default_factory=tuple)
    networks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StoragePlan:
    volumes: tuple[str, ...]
    root: str = "/srv/data/services"


@dataclass(frozen=True)
class NetworkPlan:
    networks: tuple[str, ...]
    reverse_proxy_network: str = "edge"


class ManifestValidationError(ValueError):
    pass


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _require_sequence(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ManifestValidationError(f"{field_name} must be a list of strings.")
    result: list[str] = []
    for item in value:
        result.append(_require_str(item, field_name))
    return tuple(result)


def _require_mapping(value: Any, field_name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{field_name} must be a mapping of strings.")
    result: dict[str, str] = {}
    for key, item in value.items():
        result[_require_str(key, field_name)] = _require_str(item, field_name)
    return result


def validate_manifest_schema(data: dict[str, Any]) -> None:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ManifestValidationError(f"manifest schema validation failed: {exc.message}") from exc


def load_manifest(data: dict[str, Any]) -> InfrastructureManifest:
    validate_manifest_schema(data)

    name = _require_str(data.get("name"), "name")

    raw_services = data.get("services")
    if not isinstance(raw_services, list) or not raw_services:
        raise ManifestValidationError("services must be a non-empty list.")

    services: list[ServiceDeclaration] = []
    seen_names: set[str] = set()
    for raw_service in raw_services:
        if not isinstance(raw_service, dict):
            raise ManifestValidationError("each service must be a mapping.")

        service_name = _require_str(raw_service.get("name"), "service.name")
        if service_name in seen_names:
            raise ManifestValidationError(f"duplicate service declaration: {service_name}")
        seen_names.add(service_name)

        raw_build = raw_service.get("build")
        if raw_build is not None and not isinstance(raw_build, dict):
            raise ManifestValidationError("service.build must be a mapping when provided.")
        services.append(
            ServiceDeclaration(
                name=service_name,
                image=_require_str(raw_service.get("image"), "service.image") if raw_service.get("image") is not None else None,
                build=(
                    BuildDeclaration(
                        context=_require_str(raw_build.get("context"), "service.build.context"),
                        dockerfile=_require_str(raw_build.get("dockerfile", "Dockerfile"), "service.build.dockerfile"),
                    )
                    if isinstance(raw_build, dict)
                    else None
                ),
                depends_on=_require_sequence(raw_service.get("depends_on"), "service.depends_on"),
                volumes=_require_sequence(raw_service.get("volumes"), "service.volumes"),
                networks=_require_sequence(raw_service.get("networks"), "service.networks"),
                command=(
                    _require_str(raw_service.get("command"), "service.command")
                    if raw_service.get("command") is not None
                    else None
                ),
                entrypoint=(
                    _require_str(raw_service.get("entrypoint"), "service.entrypoint")
                    if raw_service.get("entrypoint") is not None
                    else None
                ),
                ports=_require_sequence(raw_service.get("ports"), "service.ports"),
                environment=tuple(_require_mapping(raw_service.get("environment"), "service.environment").items()),
                healthcheck=(
                    _require_str(raw_service.get("healthcheck"), "service.healthcheck")
                    if raw_service.get("healthcheck") is not None
                    else None
                ),
            )
        )

    volumes = _require_sequence(data.get("volumes"), "volumes")
    networks = _require_sequence(data.get("networks"), "networks")

    service_names = {service.name for service in services}
    for service in services:
        missing_dependencies = [
            dependency
            for dependency in service.depends_on
            if dependency not in service_names
        ]
        if missing_dependencies:
            missing = ", ".join(sorted(missing_dependencies))
            raise ManifestValidationError(
                f"service {service.name} depends on unknown services: {missing}"
            )

    declared_volumes = set(volumes)
    declared_networks = set(networks)
    for service in services:
        missing_volumes = [
            volume
            for volume in service.volumes
            if volume not in declared_volumes
        ]
        if missing_volumes:
            missing = ", ".join(sorted(missing_volumes))
            raise ManifestValidationError(
                f"service {service.name} references unknown volumes: {missing}"
            )

        missing_networks = [
            network
            for network in service.networks
            if network not in declared_networks
        ]
        if missing_networks:
            missing = ", ".join(sorted(missing_networks))
            raise ManifestValidationError(
                f"service {service.name} references unknown networks: {missing}"
            )

    return InfrastructureManifest(
        name=name,
        services=tuple(services),
        volumes=volumes,
        networks=networks,
    )


def topological_service_order(manifest: InfrastructureManifest) -> tuple[str, ...]:
    remaining = {service.name: set(service.depends_on) for service in manifest.services}
    ordered: list[str] = []

    while remaining:
        ready = sorted(name for name, deps in remaining.items() if not deps)
        if not ready:
            raise ManifestValidationError("service dependencies contain a cycle.")
        ordered.extend(ready)
        for name in ready:
            remaining.pop(name, None)
        for deps in remaining.values():
            deps.difference_update(ready)

    return tuple(ordered)


def storage_plan(manifest: InfrastructureManifest) -> StoragePlan:
    return StoragePlan(volumes=manifest.volumes)


def network_plan(manifest: InfrastructureManifest) -> NetworkPlan:
    plan = NetworkPlan(networks=manifest.networks)
    if plan.reverse_proxy_network not in plan.networks:
        raise ManifestValidationError(
            f"reverse proxy network {plan.reverse_proxy_network!r} must be declared in networks"
        )
    return plan


def render_compose_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    services: dict[str, dict[str, Any]] = {}
    for service in manifest.services:
        service_definition: dict[str, Any] = {}
        if service.image is not None:
            service_definition["image"] = service.image
        if service.build is not None:
            service_definition["build"] = {
                "context": service.build.context,
                "dockerfile": service.build.dockerfile,
            }
        service_definition["depends_on"] = list(service.depends_on)
        service_definition["volumes"] = list(service.volumes)
        service_definition["networks"] = list(service.networks)
        service_definition["ports"] = list(service.ports)
        service_definition["environment"] = {key: value for key, value in service.environment}
        if service.command is not None:
            service_definition["command"] = service.command
        if service.entrypoint is not None:
            service_definition["entrypoint"] = service.entrypoint
        if service.healthcheck is not None:
            service_definition["healthcheck"] = {
                "test": ["CMD-SHELL", service.healthcheck],
                "interval": "30s",
                "timeout": "5s",
                "retries": 3,
            }
        if not service_definition.get("image") and not service_definition.get("build"):
            raise ManifestValidationError(f"service {service.name} must declare either image or build")
        services[service.name] = service_definition

    return {
        "name": manifest.name,
        "services": services,
        "volumes": {volume: {} for volume in manifest.volumes},
        "networks": {network: {} for network in manifest.networks},
        "storage": {
            "root": "/srv/data/services",
            "volumes": list(manifest.volumes),
        },
        "networking": {
            "networks": list(manifest.networks),
            "reverse_proxy_network": "edge",
        },
        "hooks": {
            "monitoring": {
                "service": "monitoring",
                "targets": ["metrics", "logs", "health"],
            },
            "backups": {
                "service": "backups",
                "targets": list(manifest.volumes),
            },
        },
    }


def render_compose_yaml(manifest: InfrastructureManifest) -> str:
    compose_plan = render_compose_plan(manifest)
    compose_document = {
        "name": compose_plan["name"],
        "services": compose_plan["services"],
        "volumes": compose_plan["volumes"],
        "networks": compose_plan["networks"],
        "x-aisha-hooks": compose_plan["hooks"],
    }
    return yaml.safe_dump(compose_document, sort_keys=False)


def load_manifest_from_file(path: Path) -> InfrastructureManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest file must contain a mapping.")
    return load_manifest(data)


