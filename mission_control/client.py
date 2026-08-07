from __future__ import annotations

from typing import Any

import httpx


def post_event(base_url: str, token: str, event: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(
        f'{base_url.rstrip('/')}/api/events',
        headers={'X-Mission-Control-Token': token},
        json={'event': event},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()
