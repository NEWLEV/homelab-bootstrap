# Aisha Integrations Plan

## Goal

Add a practical integration layer that makes Aisha capable of durable automation, structured tool use, and reusable operator workflows.

## Priority Order

1. n8n for scheduled and event-driven workflows.
2. MCP for standardized tool access and external system bridges.
3. Skills for reusable local procedures and operator knowledge.
4. GitHub automation and CI inspection tooling.
5. Browser automation for internal apps and dashboards.
6. Slack or email connectors for operational follow-up.

## Tools Matrix

| Layer | Tool | Why it belongs | Phase |
| --- | --- | --- | --- |
| Automation | n8n | Durable retries, triggers, schedules, and human-visible workflows | 3 |
| Tooling | MCP | Standard interface for tools, services, and external systems | 3-4 |
| Reuse | Skills | Packaged local workflows, procedures, and operator knowledge | 3-4 |
| DevOps | GitHub / Actions | Repo changes, CI, reviews, releases, and checks | 4-5 |
| UI Operations | Browser automation | Internal admin portals, dashboards, and form-based tasks | 4-5 |
| Notifications | Slack / Email | Alerts, approvals, and human follow-up | 5 |

## Repository Surface

1. define an integrations manifest for supported tools and ownership
2. add a tool capability registry for n8n, MCP, and Skills
3. connect AI platform planning to the integrations registry
4. add tests for supported integration metadata and prioritization
5. add deployment stubs for the first automations and tool bridges

## Current Operating Guidance

- Use n8n for recurring workflows that need retries and explicit approval.
- Use MCP for repository, issue, and service control surfaces.
- Use Skills for anything that should be repeatable, local, and easily invoked.
- Keep destructive or externally visible actions gated by approval.
- Prefer repository-backed config over hidden operational state.

## What The Layer Provides

- Aisha can describe which tools exist and what layer they belong to.
- Automation paths are explicit and reviewable.
- Tool access is structured instead of ad hoc.
- Repeatable work becomes reusable Skills.

