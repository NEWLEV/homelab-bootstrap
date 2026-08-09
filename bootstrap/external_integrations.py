from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class WebhookTarget:
    name: str
    transport: str
    env_var: str
    example_export: str
    use_case: str


@dataclass(frozen=True)
class ExternalIntegrationPlan:
    systems: tuple[str, ...]
    use_cases: tuple[str, ...]
    control_modes: tuple[str, ...]
    safety_rules: tuple[str, ...]
    webhook_targets: tuple[WebhookTarget, ...]
    setup_flow: tuple[str, ...]
    notes: str


def build_external_integration_plan(manifest: InfrastructureManifest) -> ExternalIntegrationPlan:
    _ = manifest
    return ExternalIntegrationPlan(
        systems=(
            "GitHub Actions",
            "browser automation",
            "Slack",
            "Discord",
            "Telegram",
            "calendar",
        ),
        use_cases=(
            "code review and CI",
            "dashboard and admin workflows",
            "alerts and approvals",
            "scheduling and reminders",
        ),
        control_modes=(
            "read-only observation",
            "approval-gated writes",
            "human follow-up",
            "automated routing",
        ),
        safety_rules=(
            "use least privilege by default",
            "request approval before visible or destructive actions",
            "log every external side effect",
        ),
        webhook_targets=(
            WebhookTarget(
                name="Slack",
                transport="incoming webhook",
                env_var="SLACK_WEBHOOK_URL",
                example_export="scripts/slack_alerts_n8n_export.json",
                use_case="team alerts, approvals, and operator follow-up",
            ),
            WebhookTarget(
                name="Discord",
                transport="channel webhook",
                env_var="DISCORD_WEBHOOK_URL",
                example_export="scripts/discord_alerts_n8n_export.json",
                use_case="ops notifications in Discord channels",
            ),
            WebhookTarget(
                name="Telegram",
                transport="bot sendMessage API",
                env_var="TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID",
                example_export="scripts/telegram_alerts_n8n_export.json",
                use_case="direct push alerts to a Telegram chat",
            ),
        ),
        setup_flow=(
            "choose the target platform",
            "create or rotate the platform webhook secret",
            "store secrets only in n8n or local runtime env",
            "import the matching example export",
            "test with a Mission Control-shaped payload",
        ),
        notes="external integrations should connect the personal OS to the outside world while keeping side effects explicit, reviewable, and easy to configure through consistent webhook patterns",
    )


def render_external_integration_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_external_integration_plan(manifest)
    return {
        "systems": list(plan.systems),
        "use_cases": list(plan.use_cases),
        "control_modes": list(plan.control_modes),
        "safety_rules": list(plan.safety_rules),
        "webhook_targets": [
            {
                "name": target.name,
                "transport": target.transport,
                "env_var": target.env_var,
                "example_export": target.example_export,
                "use_case": target.use_case,
            }
            for target in plan.webhook_targets
        ],
        "setup_flow": list(plan.setup_flow),
        "notes": plan.notes,
    }
