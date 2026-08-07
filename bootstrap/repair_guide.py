from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class RepairGuidePlan:
    issue_classes: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    escalation_rules: tuple[str, ...]
    verification_checks: tuple[str, ...]


def build_repair_guide_plan(manifest: InfrastructureManifest) -> RepairGuidePlan:
    _ = manifest
    return RepairGuidePlan(
        issue_classes=("unhealthy containers", "failed backups", "certificate expiry", "config drift", "index corruption"),
        recommended_actions=("restart the impacted service", "re-run the backup job", "renew certificates", "restore known-good config", "rebuild indexes"),
        escalation_rules=("escalate when a repair changes external state", "request approval before destructive recovery", "pause when evidence is incomplete"),
        verification_checks=("confirm service health", "check logs for recurrence", "verify backup restore", "validate search responses"),
    )


def render_repair_guide_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_repair_guide_plan(manifest)
    return {
        "issue_classes": list(plan.issue_classes),
        "recommended_actions": list(plan.recommended_actions),
        "escalation_rules": list(plan.escalation_rules),
        "verification_checks": list(plan.verification_checks),
    }
