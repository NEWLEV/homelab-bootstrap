from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class DiagnosticsPlan:
    checks: tuple[str, ...]
    signals: tuple[str, ...]
    baselines: tuple[str, ...]
    notes: str


def build_diagnostics_plan(manifest: InfrastructureManifest) -> DiagnosticsPlan:
    _ = manifest
    return DiagnosticsPlan(
        checks=("container health", "backup verification", "certificate checks", "config drift", "search quality"),
        signals=("healthchecks", "log anomalies", "restore success", "latency", "error rate"),
        baselines=("all critical containers healthy", "backups restore cleanly", "certificates valid", "search responses remain grounded"),
        notes="run diagnostics before repair or maintenance so the system can explain what changed and why",
    )


def render_diagnostics_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_diagnostics_plan(manifest)
    return {
        "checks": list(plan.checks),
        "signals": list(plan.signals),
        "baselines": list(plan.baselines),
        "notes": plan.notes,
    }
