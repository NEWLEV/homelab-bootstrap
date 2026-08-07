from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ExternalIntegrationPlan:
    systems: tuple[str, ...]
    use_cases: tuple[str, ...]
    control_modes: tuple[str, ...]
    safety_rules: tuple[str, ...]
    notes: str


def build_external_integration_plan(manifest: InfrastructureManifest) -> ExternalIntegrationPlan:
    _ = manifest
    return ExternalIntegrationPlan(
        systems=("GitHub Actions", "browser automation", "Slack/email", "calendar"),
        use_cases=("code review and CI", "dashboard and admin workflows", "alerts and approvals", "scheduling and reminders"),
        control_modes=("read-only observation", "approval-gated writes", "human follow-up", "automated routing"),
        safety_rules=("use least privilege by default", "request approval before visible or destructive actions", "log every external side effect"),
        notes="external integrations should connect the personal OS to the outside world while keeping side effects explicit and reviewable",
    )


def render_external_integration_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_external_integration_plan(manifest)
    return {
        "systems": list(plan.systems),
        "use_cases": list(plan.use_cases),
        "control_modes": list(plan.control_modes),
        "safety_rules": list(plan.safety_rules),
        "notes": plan.notes,
    }
