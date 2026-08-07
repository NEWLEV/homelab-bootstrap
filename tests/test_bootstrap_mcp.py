from bootstrap.manifests import infrastructure_manifest
from bootstrap.mcp import build_mcp_plan, render_mcp_plan


def test_build_mcp_plan_describes_tool_bridges() -> None:
    manifest = infrastructure_manifest()
    plan = build_mcp_plan(manifest)

    assert plan.service == "MCP gateway"
    assert plan.tools[0].name == "repository control"
    assert plan.tools[1].category == "workflow"
    assert plan.tools[2].access_pattern == "guarded operations with least privilege"
    assert "typed bridge" in plan.routing_notes
    assert "read-only" in plan.safety_notes


def test_render_mcp_plan_returns_tools() -> None:
    manifest = infrastructure_manifest()
    plan = render_mcp_plan(manifest)

    assert plan["service"] == "MCP gateway"
    assert plan["tools"][0]["name"] == "repository control"
    assert "structured tool access" in plan["routing_notes"]
