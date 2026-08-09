from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest
from .personal_os import render_personal_os_plan


@dataclass(frozen=True)
class WebInterfacePlan:
    pages: tuple[str, ...]
    dashboard_sections: tuple[str, ...]
    entrypoints: tuple[str, ...]
    navigation_notes: str


def build_web_interface_plan(manifest: InfrastructureManifest) -> WebInterfacePlan:
    personal_os = render_personal_os_plan(manifest)
    _ = personal_os
    return WebInterfacePlan(
        pages=("home", "assistant", "operations", "memory", "integrations", "integration webhooks", "settings"),
        dashboard_sections=("status", "tasks", "alerts", "memory", "automation", "roadmap"),
        entrypoints=("conversational command bar", "quick actions", "operations panel", "memory timeline", "integration webhook setup"),
        navigation_notes="keep the interface conversational at the top, operational in the middle, and deeply inspectable behind each panel",
    )


def render_web_interface_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_web_interface_plan(manifest)
    personal_os = render_personal_os_plan(manifest)
    return {
        "pages": list(plan.pages),
        "dashboard_sections": list(plan.dashboard_sections),
        "entrypoints": list(plan.entrypoints),
        "navigation_notes": plan.navigation_notes,
        "personal_os": personal_os,
    }
