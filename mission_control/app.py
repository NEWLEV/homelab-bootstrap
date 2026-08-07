from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sqlite3
import threading
import uuid
from typing import Any, Generator, Literal

import jsonschema
from mission_control.ui import DASHBOARD_HTML

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback
    psutil = None
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

KNOWN_EVENT_KINDS = {
    'task_started',
    'task_progress',
    'task_completed',
    'task_failed',
    'action_taken',
    'approval_requested',
    'approval_resolved',
    'alert',
}
APPROVAL_STATUSES = {'pending', 'approved', 'rejected', 'expired'}
KNOWN_RISKS = {'low', 'medium', 'high'}
DEFAULT_DB_PATH = Path(os.environ.get('MISSION_CONTROL_DATABASE', str(Path.home() / '.aisha' / 'mission-control.sqlite3')))
DEFAULT_TOKEN = os.environ.get('MISSION_CONTROL_TOKEN', '')
DEMO_SEED = os.environ.get('MC_DEMO_SEED', 'false').strip().lower() in {'1', 'true', 'yes'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Trace(BaseModel):
    model_config = {'extra': 'forbid'}
    trigger: str | None = None
    policy: str | None = None
    steps: list[str] = Field(default_factory=list)
    outcome: str | None = None


class Link(BaseModel):
    model_config = {'extra': 'forbid'}
    label: str
    href: str


class AgentEvent(BaseModel):
    model_config = {'extra': 'forbid'}
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=_now)
    agent: str
    kind: Literal['task_started', 'task_progress', 'task_completed', 'task_failed', 'action_taken', 'approval_requested', 'approval_resolved', 'alert']
    title: str
    detail: str | None = None
    progress: float | None = None
    risk: str | None = None
    trace: Trace | None = None
    links: list[Link] = Field(default_factory=list)
    correlation_id: str | None = None
    source: str | None = None


class Approval(BaseModel):
    model_config = {'extra': 'forbid'}
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_ts: str = Field(default_factory=_now)
    requested_by: str
    title: str
    summary: str | None = None
    risk: str | None = None
    diff_ref: str | None = None
    rollback_available: bool = False
    status: str = 'pending'
    resolved_by: str | None = None
    resolved_ts: str | None = None
    expires_ts: str | None = None


class ApprovalResolution(BaseModel):
    model_config = {'extra': 'forbid'}
    resolver: str = 'human'


class IngestEvent(BaseModel):
    model_config = {'extra': 'forbid'}
    event: AgentEvent


EVENT_SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / 'mission_control' / 'agent-event.schema.json').read_text(encoding='utf-8'))
APPROVAL_SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / 'mission_control' / 'approval.schema.json').read_text(encoding='utf-8'))


def _validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema.validate(instance=instance, schema=schema)


@dataclass
class Store:
    path: Path
    lock: threading.Lock

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn


store = Store(DEFAULT_DB_PATH, threading.Lock())
subscribers: list[threading.Event] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    with store.connect() as conn:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                agent TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT,
                progress REAL,
                risk TEXT,
                trace TEXT,
                links TEXT,
                correlation_id TEXT,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                created_ts TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                risk TEXT,
                diff_ref TEXT,
                rollback_available INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                resolved_by TEXT,
                resolved_ts TEXT,
                expires_ts TEXT
            );
            '''
        )
        if DEMO_SEED:
            seed_demo_data(conn)
    yield


app = FastAPI(title='Mission Control', version='0.1.0', lifespan=lifespan)


def seed_demo_data(conn: sqlite3.Connection) -> None:
    if conn.execute('SELECT COUNT(*) FROM events').fetchone()[0]:
        return
    insert_event(conn, AgentEvent(agent='ops-agent', kind='task_started', title='Checked service health', source='workflow-engine'))
    approval = Approval(requested_by='infra-agent', title='Upgrade Traefik 3.1 -> 3.3', summary='Roll forward after validation', risk='high', rollback_available=True)
    insert_approval(conn, approval)
    insert_event(conn, AgentEvent(agent='infra-agent', kind='approval_requested', title=approval.title, risk='high', source='workflow-engine', correlation_id=approval.id))


def _auth(token: str | None) -> None:
    if not DEFAULT_TOKEN:
        return
    if token != DEFAULT_TOKEN:
        raise HTTPException(status_code=401, detail='invalid token')


def _event_row(event: AgentEvent) -> tuple[Any, ...]:
    return (
        event.id,
        event.ts,
        event.agent,
        event.kind,
        event.title,
        event.detail,
        event.progress,
        event.risk,
        event.trace.model_dump_json() if event.trace else None,
        json.dumps([link.model_dump() for link in event.links]),
        event.correlation_id,
        event.source,
    )


def insert_event(conn: sqlite3.Connection, event: AgentEvent) -> None:
    payload = event.model_dump()
    _validate_schema(payload, EVENT_SCHEMA)
    if event.kind not in KNOWN_EVENT_KINDS:
        raise HTTPException(status_code=422, detail='unknown event kind')
    conn.execute('INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', _event_row(event))
    conn.commit()


def insert_approval(conn: sqlite3.Connection, approval: Approval) -> None:
    _validate_schema(approval.model_dump(), APPROVAL_SCHEMA)
    conn.execute(
        'INSERT OR REPLACE INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            approval.id,
            approval.created_ts,
            approval.requested_by,
            approval.title,
            approval.summary,
            approval.risk,
            approval.diff_ref,
            1 if approval.rollback_available else 0,
            approval.status,
            approval.resolved_by,
            approval.resolved_ts,
            approval.expires_ts,
        ),
    )
    conn.commit()


def fetch_events(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute('SELECT * FROM events ORDER BY ts DESC LIMIT ?', (limit,)).fetchall()
    return [dict(row) for row in rows]


def fetch_approvals(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute('SELECT * FROM approvals WHERE status = ? ORDER BY created_ts DESC', (status,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM approvals ORDER BY created_ts DESC').fetchall()
    return [dict(row) for row in rows]


def _notify() -> None:
    for event in list(subscribers):
        event.set()


@app.get('/', include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


@app.get('/healthz')
def healthz() -> JSONResponse:
    return JSONResponse({'status': 'ok'})


@app.get('/ready')
def ready() -> JSONResponse:
    with store.connect() as conn:
        tables = {row['name'] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        events_ready = 'events' in tables
        approvals_ready = 'approvals' in tables
    return JSONResponse({'status': 'ok' if events_ready and approvals_ready else 'degraded', 'ready': events_ready and approvals_ready, 'events_ready': events_ready, 'approvals_ready': approvals_ready})


@app.post('/api/events')
def post_event(payload: IngestEvent, x_mission_control_token: str | None = Header(default=None)) -> JSONResponse:
    _auth(x_mission_control_token)
    with store.lock, store.connect() as conn:
        insert_event(conn, payload.event)
    _notify()
    return JSONResponse({'status': 'accepted', 'id': payload.event.id})


@app.get('/api/events')
def get_events(limit: int = Query(default=50, ge=1, le=200), since: str | None = None) -> JSONResponse:
    with store.connect() as conn:
        rows = fetch_events(conn, limit=limit)
    if since:
        rows = [row for row in rows if row['ts'] > since]
    return JSONResponse({'items': rows})


@app.get('/api/approvals')
def get_approvals(status: str | None = None) -> JSONResponse:
    if status and status not in APPROVAL_STATUSES:
        raise HTTPException(status_code=422, detail='invalid status')
    with store.connect() as conn:
        rows = fetch_approvals(conn, status=status)
    return JSONResponse({'items': rows})


@app.post('/api/approvals/{approval_id}/approve')
def approve_approval(approval_id: str, resolution: ApprovalResolution, confirm: bool = False) -> JSONResponse:
    return _resolve_approval(approval_id, 'approved', resolution.resolver, confirm=confirm)


@app.post('/api/approvals/{approval_id}/reject')
def reject_approval(approval_id: str, resolution: ApprovalResolution, confirm: bool = False) -> JSONResponse:
    return _resolve_approval(approval_id, 'rejected', resolution.resolver, confirm=confirm)


def _resolve_approval(approval_id: str, status: str, resolver: str, confirm: bool = False) -> JSONResponse:
    with store.lock, store.connect() as conn:
        row = conn.execute('SELECT * FROM approvals WHERE id = ?', (approval_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail='approval not found')
        if row['status'] != 'pending':
            raise HTTPException(status_code=409, detail='approval already resolved')
        if row['risk'] in {'medium', 'high'} and not confirm:
            raise HTTPException(status_code=400, detail='explicit confirm=true is required for medium and high risk approvals')
        conn.execute('UPDATE approvals SET status = ?, resolved_by = ?, resolved_ts = ? WHERE id = ?', (status, resolver, _now(), approval_id))
        conn.commit()
        insert_event(conn, AgentEvent(agent=row['requested_by'], kind='approval_resolved', title=row['title'], detail=f'approval {status}', source='manual', correlation_id=approval_id))
    _notify()
    return JSONResponse({'status': status, 'id': approval_id})


@app.get('/api/vitals')
def vitals() -> JSONResponse:
    if psutil is None:
        return JSONResponse({
            'cpu_percent': None,
            'soc_temp_c': None,
            'throttle_state': 'unknown',
            'ram_percent': None,
            'disk_percent': None,
            'containers_healthy': 0,
            'containers_total': 0,
        })
    cpu = psutil.cpu_percent(interval=0.0)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(str(store.path.parent))
    temp = None
    try:
        temps = psutil.sensors_temperatures()
        for items in temps.values():
            if items:
                temp = items[0].current
                break
    except Exception:
        temp = None
    return JSONResponse({
        'cpu_percent': cpu,
        'soc_temp_c': temp,
        'throttle_state': 'unknown',
        'ram_percent': ram.percent,
        'disk_percent': disk.percent,
        'containers_healthy': 0,
        'containers_total': 0,
    })


@app.get('/api/digest')
def digest(since: str | None = None) -> JSONResponse:
    with store.connect() as conn:
        events = fetch_events(conn, limit=500)
        approvals = fetch_approvals(conn, status='pending')
    if since:
        events = [row for row in events if row['ts'] > since]
    return JSONResponse({
        'tasks': sum(1 for event in events if event['kind'] == 'task_completed'),
        'auto_fixes': sum(1 for event in events if event['kind'] == 'action_taken'),
        'failures': sum(1 for event in events if event['kind'] == 'task_failed'),
        'prs_opened': sum(1 for event in events if 'PR' in (event['title'] or '')),
        'pending_approvals': len(approvals),
        'notable_events': events[:5],
    })


@app.get('/api/stream')
async def stream(request: Request) -> StreamingResponse:
    wake = threading.Event()
    subscribers.append(wake)

    async def generator() -> Generator[str, None, None]:
        try:
            yield 'event: ready\ndata: {}\n\n'
            while True:
                if await request.is_disconnected():
                    break
                if wake.wait(timeout=10):
                    wake.clear()
                    yield 'event: refresh\ndata: {}\n\n'
                else:
                    yield ': keepalive\n\n'
                    await asyncio.sleep(0)
        finally:
            if wake in subscribers:
                subscribers.remove(wake)

    return StreamingResponse(generator(), media_type='text/event-stream')
