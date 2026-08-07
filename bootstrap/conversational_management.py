from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class ConversationalManagementPlan:
    intents: tuple[str, ...]
    managed_domains: tuple[str, ...]
    response_modes: tuple[str, ...]
    escalation_rules: tuple[str, ...]
    notes: str


def build_conversational_management_plan(manifest: InfrastructureManifest) -> ConversationalManagementPlan:
    _ = manifest
    return ConversationalManagementPlan(
        intents=("status lookup", "task creation", "system summary", "maintenance reminder", "repair request"),
        managed_domains=("AI platform", "agent platform", "memory", "operations", "integrations"),
        response_modes=("direct answer", "action plan", "clarifying question", "approval request"),
        escalation_rules=("ask for approval before external side effects", "escalate when a request is ambiguous", "hand off to a workflow when repeated actions are needed"),
        notes="conversation should translate user requests into managed platform actions while preserving provenance and approvals",
    )


def render_conversational_management_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_conversational_management_plan(manifest)
    return {
        "intents": list(plan.intents),
        "managed_domains": list(plan.managed_domains),
        "response_modes": list(plan.response_modes),
        "escalation_rules": list(plan.escalation_rules),
        "notes": plan.notes,
    }
