from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backup import render_backup_plan
from .executor import build_phase_payload
from .infrastructure import InfrastructureManifest
from .readiness import render_readiness_summary


@dataclass(frozen=True)
class BootstrapReport:
    manifest: str
    service_order: tuple[str, ...]
    phase_names: tuple[str, ...]
    storage_root: str
    volume_names: tuple[str, ...]
    network_names: tuple[str, ...]
    compose_output: str
    hooks: dict[str, Any]
    backup_plan: dict[str, Any]
    readiness: dict[str, Any]



def build_bootstrap_report(manifest: InfrastructureManifest, output_path: Path) -> BootstrapReport:
    payload = build_phase_payload(manifest)
    return BootstrapReport(
        manifest=manifest.name,
        service_order=tuple(payload["service_order"]),
        phase_names=tuple(payload["phases"].keys()),
        storage_root=payload["storage"].root,
        volume_names=manifest.volumes,
        network_names=manifest.networks,
        compose_output=output_path.as_posix(),
        hooks=payload["compose"]["hooks"],
        backup_plan=render_backup_plan(manifest),
        readiness=render_readiness_summary(manifest, output_path, output_path.with_suffix(".ready.json"), output_path.parent / "bundle"),
    )
