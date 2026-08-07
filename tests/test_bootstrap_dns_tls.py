from pathlib import Path

from bootstrap.dns_tls import build_dns_tls_plan, render_dns_tls_plan
from bootstrap.manifests import infrastructure_manifest


def test_build_dns_tls_plan_describes_edge_certificate_handling() -> None:
    manifest = infrastructure_manifest()
    plan = build_dns_tls_plan(manifest)

    assert plan.service == "reverse-proxy"
    assert "split-horizon" in plan.dns_strategy
    assert "ACME" in plan.certificate_source or "certificate authority" in plan.certificate_source
    assert plan.domain_boundaries == ("public", "private")
    assert "public traffic terminates at edge" in plan.exposure_boundary


def test_render_dns_tls_plan_returns_renewal_notes() -> None:
    manifest = infrastructure_manifest()
    plan = render_dns_tls_plan(manifest)

    assert plan["service"] == "reverse-proxy"
    assert "renew certificates" in plan["renewal_notes"]
    assert "internal networks" in plan["exposure_boundary"]
