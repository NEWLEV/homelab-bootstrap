from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

MISSION_CONTROL_URL = os.environ.get("MISSION_CONTROL_URL", "http://127.0.0.1:8020").rstrip("/")
MISSION_CONTROL_TOKEN = os.environ.get("MISSION_CONTROL_TOKEN", "")
MISSION_CONTROL_PUBLIC_URL = os.environ.get("MISSION_CONTROL_PUBLIC_URL", "http://aisha:8000/platform/mission-control").rstrip("/")
DISPATCH_INTERVAL_SECONDS = max(5, int(os.environ.get("INTEGRATION_DISPATCH_INTERVAL_SECONDS", "30")))
STATE_PATH = Path(os.environ.get("INTEGRATION_DISPATCH_STATE", str(Path.home() / ".local" / "share" / "aisha" / "integration-dispatch-state.json")))

TARGETS = [
    {"name": "slack", "url": os.environ.get("SLACK_ALERT_WEBHOOK_URL", "").strip()},
    {"name": "discord", "url": os.environ.get("DISCORD_ALERT_WEBHOOK_URL", "").strip()},
    {"name": "telegram", "url": os.environ.get("TELEGRAM_ALERT_WEBHOOK_URL", "").strip()},
]


def _headers() -> dict[str, str]:
    if not MISSION_CONTROL_TOKEN:
        return {}
    return {"X-Mission-Control-Token": MISSION_CONTROL_TOKEN}


def load_state() -> dict[str, list[str]]:
    if not STATE_PATH.exists():
        return {"events": [], "approvals": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"events": [], "approvals": []}


def save_state(state: dict[str, list[str]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def build_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": event.get("kind", "event"),
        "title": event.get("title") or "Untitled event",
        "summary": event.get("detail") or f"{event.get('agent', 'unknown')} reported {event.get('kind', 'event')}",
        "detail": event.get("detail") or "",
        "risk": event.get("risk") or "low",
        "agent": event.get("agent") or "unknown",
        "source": event.get("source") or "mission-control",
        "event_id": event.get("id"),
        "dashboard_url": MISSION_CONTROL_PUBLIC_URL,
        "text": f"Mission Control {event.get('kind', 'event')}: {event.get('title') or 'Untitled event'}",
    }


def build_approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
    approval_id = approval.get("id", "")
    return {
        "kind": "approval_requested",
        "title": approval.get("title") or "Approval requested",
        "summary": approval.get("summary") or f"Approval requested by {approval.get('requested_by', 'unknown')}",
        "detail": approval.get("summary") or "Review and resolve this request in Mission Control.",
        "risk": approval.get("risk") or "unspecified",
        "requested_by": approval.get("requested_by") or "unknown",
        "approval_id": approval_id,
        "dashboard_url": MISSION_CONTROL_PUBLIC_URL,
        "approval_url": f"{MISSION_CONTROL_PUBLIC_URL}",
        "text": f"Mission Control approval: {approval.get('title') or 'Approval requested'}",
    }


def _post_targets(payload: dict[str, Any]) -> None:
    for target in TARGETS:
        if not target["url"]:
            continue
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(target["url"], json=payload).raise_for_status()
        except Exception as exc:
            print(f"dispatch failed for {target['name']}: {exc}")


def dispatch_once() -> dict[str, int]:
    state = load_state()
    headers = _headers()
    dispatched = {"events": 0, "approvals": 0}

    with httpx.Client(timeout=10.0, headers=headers) as client:
        events = client.get(f"{MISSION_CONTROL_URL}/api/events?limit=50").json().get("items", [])
        approvals = client.get(f"{MISSION_CONTROL_URL}/api/approvals?status=pending").json().get("items", [])

    seen_events = set(state.get("events", []))
    seen_approvals = set(state.get("approvals", []))

    for event in reversed(events):
        event_id = event.get("id")
        if not event_id or event_id in seen_events:
            continue
        _post_targets(build_event_payload(event))
        seen_events.add(event_id)
        dispatched["events"] += 1

    for approval in reversed(approvals):
        approval_id = approval.get("id")
        if not approval_id or approval_id in seen_approvals:
            continue
        _post_targets(build_approval_payload(approval))
        seen_approvals.add(approval_id)
        dispatched["approvals"] += 1

    state["events"] = list(seen_events)[-500:]
    state["approvals"] = list(seen_approvals)[-200:]
    save_state(state)
    return dispatched


def main() -> None:
    run_once = os.environ.get("INTEGRATION_DISPATCH_ONCE", "false").strip().lower() in {"1", "true", "yes"}
    if run_once:
        result = dispatch_once()
        print(json.dumps(result, indent=2))
        return

    while True:
        result = dispatch_once()
        print(json.dumps(result, indent=2))
        time.sleep(DISPATCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
