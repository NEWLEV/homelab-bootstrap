from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .ai_platform import render_ai_platform_plan
from .ai_services import render_ai_services_compose_yaml, render_ai_services_plan
from .backup import render_backup_plan
from .bundle import write_bootstrap_bundle
from .dns_tls import render_dns_tls_plan
from .exposure import render_exposure_plan
from .executor import build_phase_payload, run_infrastructure_phases
from .graph import render_dependency_graph
from .ingestion import render_ingestion_plan
from .infrastructure import ManifestValidationError, SCHEMA_PATH, load_manifest_from_file, render_compose_yaml
from .integrations import render_integration_registry
from .local_rag import render_local_rag_plan
from .mcp import render_mcp_plan
from .monitoring import render_monitoring_plan
from .n8n import render_n8n_plan
from .rag_api import render_rag_api_plan
from .readiness import render_readiness_summary
from .report import build_bootstrap_report
from .skills import render_skills_plan
from .storage_network import render_storage_network_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aisha-bootstrap",
        description="Validate and execute the Aisha infrastructure bootstrap manifest.",
    )
    parser.add_argument("manifest", nargs="?", type=Path, default=Path("bootstrap") / "infrastructure.yaml", help="Path to the infrastructure manifest YAML file.")
    parser.add_argument("--output", type=Path, default=Path("bootstrap") / "compose.generated.yaml", help="Output path for generated files such as Compose YAML.")
    parser.add_argument("--report-output", type=Path, default=Path("bootstrap") / "bootstrap.report.json", help="Output path for the generated bootstrap report.")
    parser.add_argument("--bundle-dir", type=Path, default=Path("bootstrap") / "bundle", help="Directory for the generated bootstrap artifact bundle.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="Print the rendered infrastructure plan and exit.")
    mode.add_argument("--graph", action="store_true", help="Print the service dependency graph and exit.")
    mode.add_argument("--storage-network", action="store_true", help="Print the storage and networking plan and exit.")
    mode.add_argument("--monitoring", action="store_true", help="Print the monitoring plan and exit.")
    mode.add_argument("--exposure", action="store_true", help="Print the reverse-proxy and exposure plan and exit.")
    mode.add_argument("--dns-tls", action="store_true", help="Print the DNS and TLS plan and exit.")
    mode.add_argument("--backup-plan", action="store_true", help="Print the backup and restore plan and exit.")
    mode.add_argument("--readiness", action="store_true", help="Print the Phase 2 readiness summary and exit.")
    mode.add_argument("--status", action="store_true", help="Print the deploy-ready Phase 2 status and exit.")
    mode.add_argument("--ai-platform", action="store_true", help="Print the Phase 3 AI platform plan and exit.")
    mode.add_argument("--ai-services", action="store_true", help="Print the AI services compose plan and exit.")
    mode.add_argument("--integrations", action="store_true", help="Print the integrations registry and exit.")
    mode.add_argument("--n8n", action="store_true", help="Print the n8n workflow plan and exit.")
    mode.add_argument("--mcp", action="store_true", help="Print the MCP tool plan and exit.")
    mode.add_argument("--skills", action="store_true", help="Print the Skills plan and exit.")
    mode.add_argument("--ingestion", action="store_true", help="Print the ingestion and indexing plan and exit.")
    mode.add_argument("--local-rag", action="store_true", help="Print the local RAG runtime plan and exit.")
    mode.add_argument("--bundle", action="store_true", help="Write the bootstrap artifact bundle and exit.")
    mode.add_argument("--run", action="store_true", help="Run the infrastructure phases after loading the manifest.")
    mode.add_argument("--schema", action="store_true", help="Print the infrastructure manifest schema and exit.")
    mode.add_argument("--validate", action="store_true", help="Validate the infrastructure manifest and phase order without running phases.")
    mode.add_argument("--compose", action="store_true", help="Print the rendered Compose YAML and exit.")
    mode.add_argument("--write-compose", action="store_true", help="Write the rendered Compose YAML to the output path and exit.")
    mode.add_argument("--report", action="store_true", help="Print a structured bootstrap report and exit.")
    mode.add_argument("--write-report", action="store_true", help="Write the structured bootstrap report to disk and exit.")
    return parser


def _to_json(value: Any) -> str:
    def default(obj: Any) -> Any:
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, tuple):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(value, indent=2, sort_keys=True, default=default)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.schema:
        print(SCHEMA_PATH.read_text(encoding="utf-8"))
        return 0

    try:
        manifest = load_manifest_from_file(args.manifest)
    except (FileNotFoundError, ManifestValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.compose:
        print(render_compose_yaml(manifest), end="")
        return 0

    if args.write_compose:
        args.output.write_text(render_compose_yaml(manifest), encoding="utf-8")
        print(str(args.output))
        return 0

    if args.report:
        print(_to_json(build_bootstrap_report(manifest, args.output)))
        return 0

    if args.write_report:
        report = build_bootstrap_report(manifest, args.output)
        args.report_output.write_text(_to_json(report), encoding="utf-8")
        print(str(args.report_output))
        return 0

    if args.validate:
        payload = build_phase_payload(manifest)
        print(_to_json({"status": "valid", "manifest": manifest.name, "service_order": payload["service_order"], "phase_names": payload["phases"]}))
        return 0

    if args.graph:
        print(_to_json(render_dependency_graph(manifest)))
        return 0

    if args.storage_network:
        print(_to_json(render_storage_network_plan(manifest)))
        return 0

    if args.monitoring:
        print(_to_json(render_monitoring_plan(manifest)))
        return 0

    if args.exposure:
        print(_to_json(render_exposure_plan(manifest)))
        return 0

    if args.dns_tls:
        print(_to_json(render_dns_tls_plan(manifest)))
        return 0

    if args.backup_plan:
        print(_to_json(render_backup_plan(manifest)))
        return 0

    if args.readiness or args.status:
        readiness = render_readiness_summary(manifest, args.output, args.report_output, args.bundle_dir)
        if args.readiness:
            print(_to_json(readiness))
        else:
            print(_to_json({"manifest": manifest.name, "ready": readiness["ready"], "artifacts": readiness["artifacts"], "checks": readiness["checks"], "paths": {"compose": args.output.as_posix(), "report": args.report_output.as_posix(), "bundle_dir": args.bundle_dir.as_posix()}}))
        return 0

    if args.ai_platform:
        print(_to_json(render_ai_platform_plan(manifest)))
        return 0

    if args.ai_services:
        print(render_ai_services_compose_yaml(manifest), end="")
        return 0

    if args.integrations:
        print(_to_json(render_integration_registry(manifest)))
        return 0

    if args.n8n:
        print(_to_json(render_n8n_plan(manifest)))
        return 0

    if args.mcp:
        print(_to_json(render_mcp_plan(manifest)))
        return 0

    if args.skills:
        print(_to_json(render_skills_plan(manifest)))
        return 0

    if args.ingestion:
        print(_to_json(render_ingestion_plan(manifest)))
        return 0

    if args.local_rag:
        print(_to_json(render_local_rag_plan(manifest)))
        return 0

    if args.bundle:
        bundle = write_bootstrap_bundle(manifest, args.bundle_dir)
        print(_to_json({"bundle_dir": bundle.bundle_dir.as_posix(), "compose_path": bundle.compose_path.as_posix(), "report_path": bundle.report_path.as_posix(), "graph_path": bundle.graph_path.as_posix(), "backup_path": bundle.backup_path.as_posix(), "storage_network_path": bundle.storage_network_path.as_posix(), "monitoring_path": bundle.monitoring_path.as_posix(), "exposure_path": bundle.exposure_path.as_posix(), "readiness_path": bundle.readiness_path.as_posix(), "dns_tls_path": bundle.dns_tls_path.as_posix(), "ai_platform_path": bundle.ai_platform_path.as_posix(), "ai_services_path": bundle.ai_services_path.as_posix(), "ai_services_compose_path": bundle.ai_services_compose_path.as_posix(), "rag_api_path": bundle.rag_api_path.as_posix(), "ingestion_path": bundle.ingestion_path.as_posix(), "local_rag_path": bundle.local_rag_path.as_posix(), "integrations_path": bundle.integrations_path.as_posix(), "n8n_path": bundle.n8n_path.as_posix(), "mcp_path": bundle.mcp_path.as_posix(), "skills_path": bundle.skills_path.as_posix(), "skills_registry_path": bundle.skills_registry_path.as_posix()}))
        return 0

    if args.plan:
        print(_to_json(build_phase_payload(manifest)))
        return 0

    summary = run_infrastructure_phases(manifest)
    print(_to_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
