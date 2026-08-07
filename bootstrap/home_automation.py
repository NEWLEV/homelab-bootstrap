from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class HomeAutomationPlan:
    target_systems: tuple[str, ...]
    control_surfaces: tuple[str, ...]
    sensor_sources: tuple[str, ...]
    safety_rules: tuple[str, ...]
    notes: str


def build_home_automation_plan(manifest: InfrastructureManifest) -> HomeAutomationPlan:
    _ = manifest
    return HomeAutomationPlan(
        target_systems=("Home Assistant", "MQTT", "ESPHome", "smart lighting", "power monitoring", "cameras"),
        control_surfaces=("status monitoring", "scene activation", "routine automation", "alerting", "manual override"),
        sensor_sources=("door sensors", "environmental sensors", "temperature", "motion", "power draw"),
        safety_rules=("keep external actions approval-gated", "prefer read-only observation by default", "only automate low-risk routines without confirmation"),
        notes="home automation should be observable first, controllable second, and always bounded by explicit safety policies",
    )


def render_home_automation_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_home_automation_plan(manifest)
    return {
        "target_systems": list(plan.target_systems),
        "control_surfaces": list(plan.control_surfaces),
        "sensor_sources": list(plan.sensor_sources),
        "safety_rules": list(plan.safety_rules),
        "notes": plan.notes,
    }
