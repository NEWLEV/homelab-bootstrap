from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class SkillEntry:
    name: str
    category: str
    purpose: str
    invocation: str


@dataclass(frozen=True)
class SkillsPlan:
    service: str
    skills: tuple[SkillEntry, ...]
    discovery_notes: str
    packaging_notes: str


def build_skills_plan(manifest: InfrastructureManifest) -> SkillsPlan:
    _ = manifest
    return SkillsPlan(
        service="Skills registry",
        skills=(
            SkillEntry(
                name="bootstrap-validation",
                category="operations",
                purpose="run repeatable bootstrap checks and manifest validation flows",
                invocation="aisha skills run bootstrap-validation",
            ),
            SkillEntry(
                name="integration-review",
                category="platform",
                purpose="summarize and validate n8n, MCP, and tool registry changes",
                invocation="aisha skills run integration-review",
            ),
            SkillEntry(
                name="release-prep",
                category="devops",
                purpose="package repo changes, smoke tests, and rollout notes",
                invocation="aisha skills run release-prep",
            ),
            SkillEntry(
                name="operator-checklist",
                category="operations",
                purpose="surface guided operator checklists for recurring maintenance tasks",
                invocation="aisha skills run operator-checklist",
            ),
        ),
        discovery_notes="discover Skills from repository-backed manifests and keep them visible to automation, agents, and operators",
        packaging_notes="package Skills as repeatable local procedures with explicit metadata, versioning, and approval boundaries",
    )


def render_skills_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_skills_plan(manifest)
    return {
        "service": plan.service,
        "skills": [
            {
                "name": skill.name,
                "category": skill.category,
                "purpose": skill.purpose,
                "invocation": skill.invocation,
            }
            for skill in plan.skills
        ],
        "discovery_notes": plan.discovery_notes,
        "packaging_notes": plan.packaging_notes,
    }
