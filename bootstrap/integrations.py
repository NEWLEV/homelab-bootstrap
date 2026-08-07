from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class IntegrationEntry:
    name: str
    layer: str
    purpose: str
    priority: int
    phase: str


@dataclass(frozen=True)
class IntegrationRegistry:
    entries: tuple[IntegrationEntry, ...]
    summary: str


def build_integration_registry(manifest: InfrastructureManifest) -> IntegrationRegistry:
    _ = manifest
    return IntegrationRegistry(
        entries=(
            IntegrationEntry(
                name="n8n",
                layer="automation",
                purpose="durable workflow orchestration and retryable operational automations",
                priority=1,
                phase="Phase 3",
            ),
            IntegrationEntry(
                name="MCP",
                layer="tooling",
                purpose="structured tool access and external system bridges",
                priority=2,
                phase="Phase 3",
            ),
            IntegrationEntry(
                name="Skills",
                layer="reuse",
                purpose="packaged local procedures and repeatable operator knowledge",
                priority=3,
                phase="Phase 3",
            ),
            IntegrationEntry(
                name="GitHub Actions",
                layer="devops",
                purpose="CI, reviews, and release automation",
                priority=4,
                phase="Phase 4",
            ),
            IntegrationEntry(
                name="browser automation",
                layer="operations",
                purpose="internal admin UIs, dashboards, and browser-driven workflows",
                priority=5,
                phase="Phase 4",
            ),
            IntegrationEntry(
                name="Slack/email",
                layer="notifications",
                purpose="alerts, approvals, and human follow-up",
                priority=6,
                phase="Phase 5",
            ),
        ),
        summary="Aisha should prefer durable workflows, structured tools, and reusable local capabilities before ad hoc manual operations.",
    )


def render_integration_registry(manifest: InfrastructureManifest) -> dict[str, Any]:
    registry = build_integration_registry(manifest)
    return {
        "summary": registry.summary,
        "entries": [
            {
                "name": entry.name,
                "layer": entry.layer,
                "purpose": entry.purpose,
                "priority": entry.priority,
                "phase": entry.phase,
            }
            for entry in registry.entries
        ],
    }
