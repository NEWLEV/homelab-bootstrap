from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class SelfHealingPlan:
    triggers: tuple[str, ...]
    phases: tuple[str, ...]
    repair_actions: tuple[str, ...]
    verification_steps: tuple[str, ...]
    escalation_rules: tuple[str, ...]


def build_self_healing_plan(manifest: InfrastructureManifest) -> SelfHealingPlan:
    _ = manifest
    return SelfHealingPlan(
        triggers=("unhealthy container", "backup failure", "certificate expiry", "search degradation"),
        phases=("detect", "assess", "repair", "verify", "escalate"),
        repair_actions=("restart the impacted service", "re-run the failing job", "restore the latest good snapshot", "rebuild indexes"),
        verification_steps=("confirm healthcheck passes", "confirm logs are clean", "confirm restore succeeds", "confirm search quality recovers"),
        escalation_rules=("escalate when recovery changes persistent state", "pause when incident scope is unclear", "request approval for destructive restoration"),
    )


def render_self_healing_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_self_healing_plan(manifest)
    return {
        "triggers": list(plan.triggers),
        "phases": list(plan.phases),
        "repair_actions": list(plan.repair_actions),
        "verification_steps": list(plan.verification_steps),
        "escalation_rules": list(plan.escalation_rules),
    }
