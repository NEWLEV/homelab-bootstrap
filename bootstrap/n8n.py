from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class N8nPlan:
    service: str
    workflows: tuple[str, ...]
    triggers: tuple[str, ...]
    notification_targets: tuple[str, ...]
    example_exports: tuple[str, ...]
    retry_strategy: str
    approval_strategy: str


def build_n8n_plan(manifest: InfrastructureManifest) -> N8nPlan:
    _ = manifest
    return N8nPlan(
        service="n8n",
        workflows=(
            "nightly backups",
            "index rebuilds",
            "dependency checks",
            "security scans",
            "operational alerts",
            "Slack approval routing",
        ),
        triggers=(
            "schedule",
            "webhook",
            "manual approval",
            "event routing",
        ),
        notification_targets=(
            "Slack incoming webhook",
            "email digest",
        ),
        example_exports=(
            "scripts/mission_control_n8n_export.json",
            "scripts/slack_alerts_n8n_export.json",
        ),
        retry_strategy="retry transient failures with explicit logging and bounded attempts",
        approval_strategy="require approval for destructive, externally visible, or state-changing actions",
    )


def render_n8n_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_n8n_plan(manifest)
    return {
        "service": plan.service,
        "workflows": list(plan.workflows),
        "triggers": list(plan.triggers),
        "notification_targets": list(plan.notification_targets),
        "example_exports": list(plan.example_exports),
        "retry_strategy": plan.retry_strategy,
        "approval_strategy": plan.approval_strategy,
    }
