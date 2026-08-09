from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

MISSION_CONTROL_URL = os.environ.get("MISSION_CONTROL_URL", "http://127.0.0.1:8020").rstrip("/")
MISSION_CONTROL_TOKEN = os.environ.get("MISSION_CONTROL_TOKEN", "")
MISSION_CONTROL_DATABASE = os.environ.get("MISSION_CONTROL_DATABASE")


def _headers() -> dict[str, str]:
    if not MISSION_CONTROL_TOKEN:
        return {}
    return {"X-Mission-Control-Token": MISSION_CONTROL_TOKEN}


def _ts(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _post_event(client: httpx.Client, event: dict[str, object]) -> None:
    response = client.post(f"{MISSION_CONTROL_URL}/api/events", json={"event": event})
    response.raise_for_status()


def _insert_demo_approval() -> str:
    if MISSION_CONTROL_DATABASE:
        os.environ["MISSION_CONTROL_DATABASE"] = MISSION_CONTROL_DATABASE

    import importlib

    module = importlib.import_module("mission_control.app")
    mission_control_app = importlib.reload(module)

    approval = mission_control_app.Approval(
        id="demo-approval-traefik-upgrade",
        requested_by="infra-agent",
        title="Upgrade Traefik 3.1 -> 3.3",
        summary="Roll forward after validation; rollback package is ready if the health checks regress.",
        risk="high",
        diff_ref="/platform/integration-webhooks",
        rollback_available=True,
    )
    with mission_control_app.store.lock, mission_control_app.store.connect() as conn:
        mission_control_app.insert_approval(conn, approval)
    return approval.id


def seed_demo_data() -> None:
    headers = _headers()
    approval_id = _insert_demo_approval()
    events = [
        {
            "id": "demo-event-backup-started",
            "ts": _ts(42),
            "agent": "ops-agent",
            "kind": "task_started",
            "title": "Nightly backup verification started",
            "detail": "Reviewing the latest snapshot integrity and restore metadata.",
            "source": "workflow-engine",
            "trace": {
                "trigger": "nightly schedule",
                "policy": "backup-verification",
                "steps": ["discover snapshots", "verify manifest", "check restore target"],
                "outcome": "running",
            },
        },
        {
            "id": "demo-event-backup-progress",
            "ts": _ts(36),
            "agent": "ops-agent",
            "kind": "task_progress",
            "title": "Nightly backup verification",
            "detail": "3 of 5 backup targets validated successfully.",
            "progress": 0.6,
            "source": "workflow-engine",
        },
        {
            "id": "demo-event-integration-action",
            "ts": _ts(24),
            "agent": "coding-agent",
            "kind": "action_taken",
            "title": "Prepared integration webhook scaffolding",
            "detail": "Added shared Slack, Discord, and Telegram webhook exports for Mission Control.",
            "source": "n8n",
            "links": [
                {"label": "Integration webhooks", "href": f"{MISSION_CONTROL_URL}/platform/integration-webhooks"}
            ],
        },
        {
            "id": "demo-event-container-alert",
            "ts": _ts(10),
            "agent": "ops-agent",
            "kind": "alert",
            "title": "Container cleanup recommendation",
            "detail": "14 unused images can be pruned during the next maintenance window.",
            "risk": "low",
            "source": "workflow-engine",
        },
        {
            "id": "demo-event-approval-requested",
            "ts": _ts(5),
            "agent": "infra-agent",
            "kind": "approval_requested",
            "title": "Upgrade Traefik 3.1 -> 3.3",
            "detail": "Roll forward after validation; rollback package is ready if the health checks regress.",
            "risk": "high",
            "correlation_id": approval_id,
            "source": "workflow-engine",
        },
    ]

    with httpx.Client(timeout=10.0, headers=headers) as client:
        for event in events:
            _post_event(client, event)

    print("Seeded Mission Control demo events and a pending approval.")


if __name__ == "__main__":
    seed_demo_data()
