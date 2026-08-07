from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class MonitoringPlan:
    service: str
    metric_targets: tuple[str, ...]
    dashboard_expectations: tuple[str, ...]
    alerting_targets: tuple[str, ...]
    log_sources: tuple[str, ...]
    hooks: dict[str, tuple[str, ...]]


def build_monitoring_plan(manifest: InfrastructureManifest) -> MonitoringPlan:
    service_names = tuple(service.name for service in manifest.services)
    return MonitoringPlan(
        service="monitoring",
        metric_targets=("cpu", "memory", "storage", "network", "service_health"),
        dashboard_expectations=(
            "service availability",
            "request latency",
            "resource utilization",
        ),
        alerting_targets=("containers", "healthchecks", "backups"),
        log_sources=service_names,
        hooks={
            "scrape": ("metrics", "health", "logs"),
            "alert": ("containers", "healthchecks", "backups"),
        },
    )


def render_monitoring_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_monitoring_plan(manifest)
    return {
        "service": plan.service,
        "metric_targets": list(plan.metric_targets),
        "dashboard_expectations": list(plan.dashboard_expectations),
        "alerting_targets": list(plan.alerting_targets),
        "log_sources": list(plan.log_sources),
        "collection_notes": "monitor health and operational status without manual inspection",
        "hooks": {key: list(value) for key, value in plan.hooks.items()},
    }
