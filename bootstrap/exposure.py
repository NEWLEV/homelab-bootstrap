from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ExposurePlan:
    service: str
    public_entrypoint: str
    tls_terminator: str
    dns_strategy: str
    exposed_services: tuple[str, ...]
    internal_services: tuple[str, ...]
    access_policy: dict[str, tuple[str, ...]]


def build_exposure_plan(manifest: InfrastructureManifest) -> ExposurePlan:
    services = tuple(service.name for service in manifest.services)
    public_services = tuple(service.name for service in manifest.services if "edge" in service.networks)
    internal_services = tuple(service.name for service in manifest.services if service.name not in public_services)
    if not public_services:
        public_services = ("reverse-proxy",)
    if not internal_services:
        internal_services = services
    return ExposurePlan(
        service="reverse-proxy",
        public_entrypoint="edge",
        tls_terminator="traefik",
        dns_strategy="split-horizon or tunnel-backed external DNS",
        exposed_services=public_services,
        internal_services=internal_services,
        access_policy={
            "public": public_services,
            "private": internal_services,
        },
    )


def render_exposure_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_exposure_plan(manifest)
    return {
        "service": plan.service,
        "public_entrypoint": plan.public_entrypoint,
        "tls_terminator": plan.tls_terminator,
        "dns_strategy": plan.dns_strategy,
        "exposed_services": list(plan.exposed_services),
        "internal_services": list(plan.internal_services),
        "access_policy": {key: list(value) for key, value in plan.access_policy.items()},
        "boundary_notes": "public services terminate at the edge proxy; all other services remain private on internal networks",
    }
