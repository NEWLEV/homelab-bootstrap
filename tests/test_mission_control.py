import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

DB_PATH = Path(r'C:/Users/ZBook/Documents/Aisha/.test-mission-control.sqlite3')
os.environ['MISSION_CONTROL_DATABASE'] = str(DB_PATH)
os.environ['MISSION_CONTROL_TOKEN'] = 'secret-token'
os.environ['MC_DEMO_SEED'] = 'false'

module = importlib.import_module('mission_control.app')
mission_control_app = importlib.reload(module)
app = mission_control_app.app


def test_healthz() -> None:
    with TestClient(app) as client:
        response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_ready() -> None:
    with TestClient(app) as client:
        response = client.get('/ready')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ok'
    assert body['ready'] is True
    assert body['events_ready'] is True
    assert body['approvals_ready'] is True


def test_event_ingest_requires_token() -> None:
    with TestClient(app) as client:
        response = client.post('/api/events', json={'event': {'agent': 'ops-agent', 'kind': 'task_started', 'title': 'started'}})
    assert response.status_code == 401


def test_event_ingest_and_schema_validation() -> None:
    with TestClient(app) as client:
        response = client.post('/api/events', headers={'X-Mission-Control-Token': 'secret-token'}, json={'event': {'agent': 'ops-agent', 'kind': 'task_started', 'title': 'started'}})
        assert response.status_code == 200
        assert response.json()['status'] == 'accepted'

        bad = client.post('/api/events', headers={'X-Mission-Control-Token': 'secret-token'}, json={'event': {'agent': 'ops-agent', 'kind': 'not-real', 'title': 'bad'}})
        assert bad.status_code == 422

        extra = client.post('/api/events', headers={'X-Mission-Control-Token': 'secret-token'}, json={'event': {'agent': 'ops-agent', 'kind': 'task_started', 'title': 'bad', 'unexpected': True}})
        assert extra.status_code == 422


def test_approval_state_machine() -> None:
    with TestClient(app) as client:
        created = mission_control_app.Approval(requested_by='infra-agent', title='Upgrade Traefik', risk='high')
        with mission_control_app.store.connect() as conn:
            mission_control_app.insert_approval(conn, created)

        no_confirm = client.post(f'/api/approvals/{created.id}/approve', json={'resolver': 'alice'})
        assert no_confirm.status_code == 400

        response = client.post(f'/api/approvals/{created.id}/approve?confirm=true', json={'resolver': 'alice'})
        assert response.status_code == 200
        assert response.json()['status'] == 'approved'

        again = client.post(f'/api/approvals/{created.id}/reject?confirm=true', json={'resolver': 'alice'})
        assert again.status_code == 409


def test_digest_and_vitals_and_sse() -> None:
    with TestClient(app) as client:
        vitals = client.get('/api/vitals')
        assert vitals.status_code == 200
        assert 'cpu_percent' in vitals.json()

        digest = client.get('/api/digest')
        assert digest.status_code == 200
        assert 'pending_approvals' in digest.json()

    assert any(route.path == '/api/stream' for route in app.routes)


def test_dashboard_uses_mount_relative_api_paths() -> None:
    with TestClient(app) as client:
        response = client.get('/')

    assert response.status_code == 200
    assert "fetch('api/events?limit=30')" in response.text
    assert "new EventSource('api/stream')" in response.text
    assert 'href="api/events"' in response.text
    assert 'href="/api/events"' not in response.text
