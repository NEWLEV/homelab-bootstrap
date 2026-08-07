from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backup import render_backup_plan
from .exposure import render_exposure_plan
from .monitoring import render_monitoring_plan
from .storage_network import render_storage_network_plan
from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ReadinessSummary:
    manifest: str
    ready: bool
    checks: dict[str, bool]
    artifacts: dict[str, str]
    notes: tuple[str, ...]


def build_readiness_summary(manifest: InfrastructureManifest, compose_output: Path, report_output: Path, bundle_dir: Path) -> ReadinessSummary:
    storage_network = render_storage_network_plan(manifest)
    monitoring = render_monitoring_plan(manifest)
    exposure = render_exposure_plan(manifest)
    backup = render_backup_plan(manifest)
    checks = {
        "storage": bool(storage_network["storage"]["volumes"]),
        "networking": bool(storage_network["networking"]["networks"]),
        "monitoring": bool(monitoring["metric_targets"]),
        "monitoring_hooks": bool(monitoring.get("hooks")),
        "exposure": bool(exposure["exposed_services"]),
        "backup": bool(backup["volume_names"]),
        "backup_hooks": bool(backup.get("hooks")),
        "compose": bool(compose_output),
        "report": bool(report_output),
        "bundle": bool(bundle_dir),
    }
    return ReadinessSummary(
        manifest=manifest.name,
        ready=all(checks.values()),
        checks=checks,
        artifacts={
            "compose": compose_output.as_posix(),
            "report": report_output.as_posix(),
            "bundle_dir": bundle_dir.as_posix(),
        },
        notes=(
            "Phase 2 core services are described in repository-managed config.",
            "Storage, networking, monitoring, exposure, and backup plans are explicit.",
            "Operational hooks for monitoring and backup verification are wired in.",
        ),
    )


def render_readiness_summary(manifest: InfrastructureManifest, compose_output: Path, report_output: Path, bundle_dir: Path) -> dict[str, Any]:
    summary = build_readiness_summary(manifest, compose_output, report_output, bundle_dir)
    return {
        "manifest": summary.manifest,
        "ready": summary.ready,
        "checks": summary.checks,
        "artifacts": summary.artifacts,
        "notes": list(summary.notes),
    }
