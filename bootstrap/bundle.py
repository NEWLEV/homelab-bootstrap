from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ai_platform import render_ai_platform_plan
from .ai_services import render_ai_services_compose_yaml, render_ai_services_plan
from .backup import render_backup_plan
from .dns_tls import render_dns_tls_plan
from .exposure import render_exposure_plan
from .graph import render_dependency_graph
from .ingestion import render_ingestion_plan
from .integrations import render_integration_registry
from .local_rag import render_local_rag_plan
from .infrastructure import InfrastructureManifest, render_compose_yaml
from .mcp import render_mcp_plan
from .monitoring import render_monitoring_plan
from .n8n import render_n8n_plan
from .rag_api import render_rag_api_plan
from .readiness import render_readiness_summary
from .report import build_bootstrap_report
from .skills import render_skills_plan
from .storage_network import render_storage_network_plan


@dataclass(frozen=True)
class BootstrapBundle:
    bundle_dir: Path
    compose_path: Path
    report_path: Path
    graph_path: Path
    backup_path: Path
    storage_network_path: Path
    monitoring_path: Path
    exposure_path: Path
    readiness_path: Path
    dns_tls_path: Path
    ai_platform_path: Path
    ai_services_path: Path
    ai_services_compose_path: Path
    rag_api_path: Path
    ingestion_path: Path
    local_rag_path: Path
    integrations_path: Path
    n8n_path: Path
    mcp_path: Path
    skills_path: Path
    skills_registry_path: Path


def _json_dump(value: Any) -> str:
    def default(obj: Any) -> Any:
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, tuple):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(value, indent=2, sort_keys=True, default=default)


def write_bootstrap_bundle(manifest: InfrastructureManifest, bundle_dir: Path) -> BootstrapBundle:
    bundle_dir.mkdir(parents=True, exist_ok=True)

    compose_path = bundle_dir / "compose.generated.yaml"
    report_path = bundle_dir / "bootstrap.report.json"
    graph_path = bundle_dir / "dependency.graph.json"
    backup_path = bundle_dir / "backup.plan.json"
    storage_network_path = bundle_dir / "storage-network.plan.json"
    monitoring_path = bundle_dir / "monitoring.plan.json"
    exposure_path = bundle_dir / "exposure.plan.json"
    readiness_path = bundle_dir / "readiness.summary.json"
    dns_tls_path = bundle_dir / "dns-tls.plan.json"
    ai_platform_path = bundle_dir / "ai-platform.plan.json"
    ai_services_path = bundle_dir / "ai-services.plan.json"
    ai_services_compose_path = bundle_dir / "ai-services.compose.yaml"
    rag_api_path = bundle_dir / "rag-api.plan.json"
    ingestion_path = bundle_dir / "ingestion.plan.json"
    local_rag_path = bundle_dir / "local-rag.plan.json"
    integrations_path = bundle_dir / "integrations.registry.json"
    n8n_path = bundle_dir / "n8n.plan.json"
    mcp_path = bundle_dir / "mcp.plan.json"
    skills_path = bundle_dir / "skills.plan.json"
    skills_registry_path = bundle_dir / "skills.registry.json"

    compose_path.write_text(render_compose_yaml(manifest), encoding="utf-8")
    report_path.write_text(_json_dump(build_bootstrap_report(manifest, compose_path)), encoding="utf-8")
    graph_path.write_text(_json_dump(render_dependency_graph(manifest)), encoding="utf-8")
    backup_path.write_text(_json_dump(render_backup_plan(manifest)), encoding="utf-8")
    storage_network_path.write_text(_json_dump(render_storage_network_plan(manifest)), encoding="utf-8")
    monitoring_path.write_text(_json_dump(render_monitoring_plan(manifest)), encoding="utf-8")
    exposure_path.write_text(_json_dump(render_exposure_plan(manifest)), encoding="utf-8")
    readiness_path.write_text(_json_dump(render_readiness_summary(manifest, compose_path, report_path, bundle_dir)), encoding="utf-8")
    dns_tls_path.write_text(_json_dump(render_dns_tls_plan(manifest)), encoding="utf-8")
    ai_platform_path.write_text(_json_dump(render_ai_platform_plan(manifest)), encoding="utf-8")
    ai_services_path.write_text(_json_dump(render_ai_services_plan(manifest)), encoding="utf-8")
    ai_services_compose_path.write_text(render_ai_services_compose_yaml(manifest), encoding="utf-8")
    rag_api_path.write_text(_json_dump(render_rag_api_plan(manifest)), encoding="utf-8")
    ingestion_path.write_text(_json_dump(render_ingestion_plan(manifest)), encoding="utf-8")
    local_rag_path.write_text(_json_dump(render_local_rag_plan(manifest)), encoding="utf-8")
    integrations_path.write_text(_json_dump(render_integration_registry(manifest)), encoding="utf-8")
    n8n_path.write_text(_json_dump(render_n8n_plan(manifest)), encoding="utf-8")
    mcp_path.write_text(_json_dump(render_mcp_plan(manifest)), encoding="utf-8")
    skills_path.write_text(_json_dump(render_skills_plan(manifest)), encoding="utf-8")
    skills_registry_path.write_text(Path(__file__).with_name("skills.registry.json").read_text(encoding="utf-8"), encoding="utf-8")

    return BootstrapBundle(
        bundle_dir=bundle_dir,
        compose_path=compose_path,
        report_path=report_path,
        graph_path=graph_path,
        backup_path=backup_path,
        storage_network_path=storage_network_path,
        monitoring_path=monitoring_path,
        exposure_path=exposure_path,
        readiness_path=readiness_path,
        dns_tls_path=dns_tls_path,
        ai_platform_path=ai_platform_path,
        ai_services_path=ai_services_path,
        ai_services_compose_path=ai_services_compose_path,
        rag_api_path=rag_api_path,
        ingestion_path=ingestion_path,
        local_rag_path=local_rag_path,
        integrations_path=integrations_path,
        n8n_path=n8n_path,
        mcp_path=mcp_path,
        skills_path=skills_path,
        skills_registry_path=skills_registry_path,
    )
