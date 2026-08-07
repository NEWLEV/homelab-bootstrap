from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class DnsTlsPlan:
    service: str
    dns_strategy: str
    tls_strategy: str
    certificate_source: str
    domain_boundaries: tuple[str, ...]
    renewal_notes: str
    exposure_boundary: str


def build_dns_tls_plan(manifest: InfrastructureManifest) -> DnsTlsPlan:
    _ = manifest
    return DnsTlsPlan(
        service="reverse-proxy",
        dns_strategy="split-horizon DNS with optional tunnel fallback",
        tls_strategy="automatic TLS termination at the edge proxy",
        certificate_source="ACME-compatible provider or internal certificate authority",
        domain_boundaries=("public", "private"),
        renewal_notes="renew certificates before expiry and verify proxy reloads cleanly",
        exposure_boundary="public traffic terminates at edge; private services stay on internal networks",
    )


def render_dns_tls_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_dns_tls_plan(manifest)
    return {
        "service": plan.service,
        "dns_strategy": plan.dns_strategy,
        "tls_strategy": plan.tls_strategy,
        "certificate_source": plan.certificate_source,
        "domain_boundaries": list(plan.domain_boundaries),
        "renewal_notes": plan.renewal_notes,
        "exposure_boundary": plan.exposure_boundary,
    }
