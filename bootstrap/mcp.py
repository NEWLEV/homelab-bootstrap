from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class McpTool:
    name: str
    category: str
    description: str
    access_pattern: str


@dataclass(frozen=True)
class McpPlan:
    service: str
    tools: tuple[McpTool, ...]
    routing_notes: str
    safety_notes: str


def build_mcp_plan(manifest: InfrastructureManifest) -> McpPlan:
    _ = manifest
    return McpPlan(
        service="MCP gateway",
        tools=(
            McpTool(
                name="repository control",
                category="devops",
                description="read and update repository state through structured tool calls",
                access_pattern="request/response with explicit approval for writes",
            ),
            McpTool(
                name="issue and task control",
                category="workflow",
                description="manage work items, statuses, and review metadata",
                access_pattern="ticket-oriented operations with audit trails",
            ),
            McpTool(
                name="service administration",
                category="operations",
                description="bridge internal services, dashboards, and admin endpoints",
                access_pattern="guarded operations with least privilege",
            ),
            McpTool(
                name="knowledge access",
                category="knowledge",
                description="query local knowledge sources and reference material",
                access_pattern="read-only retrieval unless explicitly approved",
            ),
        ),
        routing_notes="prefer MCP when a task needs structured tool access through a stable typed bridge to an external system, repo, or service",
        safety_notes="keep writes explicit, gated, and auditable; prefer read-only access by default",
    )


def render_mcp_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_mcp_plan(manifest)
    return {
        "service": plan.service,
        "tools": [
            {
                "name": tool.name,
                "category": tool.category,
                "description": tool.description,
                "access_pattern": tool.access_pattern,
            }
            for tool in plan.tools
        ],
        "routing_notes": plan.routing_notes,
        "safety_notes": plan.safety_notes,
    }
