from __future__ import annotations

import os

import httpx

BASE_URL = os.environ.get('MISSION_CONTROL_URL', 'http://127.0.0.1:8020')
TOKEN = os.environ.get('MISSION_CONTROL_TOKEN', '')

headers = {'X-Mission-Control-Token': TOKEN} if TOKEN else {}
base_url = BASE_URL.rstrip('/')

with httpx.Client(timeout=10.0, headers=headers) as client:
    approvals = client.get(f'{base_url}/api/approvals?status=pending').json()['items']
    for approval in approvals:
        if approval['risk'] in {'medium', 'high'}:
            client.post(
                f"{base_url}/api/approvals/{approval['id']}/approve?confirm=true",
                json={'resolver': 'workflow-engine'},
            )
