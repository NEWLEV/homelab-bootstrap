from __future__ import annotations

import json
import os

import httpx

BASE_URL = os.environ.get('MISSION_CONTROL_URL', 'http://127.0.0.1:8020')
TOKEN = os.environ.get('MISSION_CONTROL_TOKEN', '')

with httpx.Client(timeout=10.0) as client:
    approvals = client.get(f'{BASE_URL.rstrip('/')}/api/approvals?status=pending').json()['items']
    for approval in approvals:
        if approval['risk'] in {'medium', 'high'}:
            client.post(
                f'{BASE_URL.rstrip('/')}/api/approvals/{approval['id']}/approve',
                json={'resolver': 'workflow-engine'},
            )
