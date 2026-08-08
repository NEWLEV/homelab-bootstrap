from __future__ import annotations

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Mission Control</title>
  <style>
    :root { --bg:#f4f2ed; --panel:#fffdf8; --panel-alt:#f7f4ef; --text:#161412; --muted:#6f6861; --border:#ded6cb; --accent:#1f5c4a; --accent-soft:#dcebe5; --danger:#a53a2a; --warning:#a36d14; --shadow:0 12px 30px rgba(24,20,15,.08); }
    @media (prefers-color-scheme: dark) { :root { --bg:#111311; --panel:#191b19; --panel-alt:#161816; --text:#f2f1ed; --muted:#a8a39b; --border:#2f322d; --accent:#7bc8a4; --accent-soft:#1b2a22; --danger:#ef8e7d; --warning:#efc56d; --shadow:0 16px 34px rgba(0,0,0,.32);} }
    * { box-sizing:border-box; }
    body { margin:0; font:14px/1.45 Inter,system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif; color:var(--text); background:radial-gradient(circle at top left, rgba(31,92,74,.08), transparent 28%), radial-gradient(circle at bottom right, rgba(163,109,20,.08), transparent 24%), var(--bg); }
    .shell { max-width:1380px; margin:0 auto; padding:24px; }
    header { display:grid; grid-template-columns:1fr auto; gap:16px; align-items:start; margin-bottom:18px; }
    h1 { margin:0 0 8px; font-size:clamp(2rem,4vw,3.8rem); letter-spacing:-.04em; }
    .lede { max-width:760px; color:var(--muted); margin:0; }
    .pill { display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border:1px solid var(--border); border-radius:999px; background:var(--panel); box-shadow:var(--shadow); color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.12em; }
    .status-dot { width:9px; height:9px; border-radius:999px; background:var(--accent); }
    .toolbar,.grid,.cards { display:grid; gap:14px; }
    .toolbar { grid-template-columns:1.6fr auto; margin:18px 0 22px; }
    .search,.panel,.card { background:var(--panel); border:1px solid var(--border); border-radius:18px; box-shadow:var(--shadow); }
    .search { padding:16px 18px; color:var(--muted); font-size:15px; }
    .search strong { color:var(--text); }
    .meta { padding:16px 18px; display:flex; align-items:center; gap:12px; color:var(--muted); }
    .reconnecting { color:var(--warning); font-weight:600; }
    .grid { grid-template-columns:1.6fr 1fr; }
    .panel { padding:18px; }
    .panel h2 { margin:0 0 14px; font-size:18px; }
    .feed-item { border-top:1px solid var(--border); padding:14px 0; display:grid; gap:8px; }
    .feed-item:first-child { border-top:0; padding-top:0; }
    .feed-head { display:flex; justify-content:space-between; gap:10px; align-items:baseline; }
    .feed-title { font-weight:700; }
    .feed-meta { color:var(--muted); font-size:12px; }
    details { border:1px solid var(--border); border-radius:14px; padding:10px 12px; background:var(--panel-alt); }
    summary { cursor:pointer; font-weight:600; }
    .trace { margin:10px 0 0; color:var(--muted); }
    .pill-mini { display:inline-flex; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:700; }
    .pill-low { background:var(--accent-soft); color:var(--accent); }
    .pill-medium { background:rgba(163,109,20,.16); color:var(--warning); }
    .pill-high { background:rgba(165,58,42,.16); color:var(--danger); }
    .cards { grid-template-columns:repeat(2, minmax(0, 1fr)); }
    .card { padding:16px; }
    .card h3,.digest h3 { margin:0 0 10px; font-size:16px; }
    .kpi { font-size:28px; font-weight:800; letter-spacing:-.04em; }
    .muted { color:var(--muted); }
    .approval-actions { display:flex; gap:8px; margin-top:12px; flex-wrap:wrap; }
    button { border:1px solid var(--border); background:var(--panel); color:var(--text); border-radius:999px; padding:8px 12px; cursor:pointer; }
    button.primary { background:var(--accent); color:#fff; border-color:transparent; }
    button.danger { background:var(--danger); color:#fff; border-color:transparent; }
    .digest { margin-top:14px; padding:16px 18px; }
    .digest-bar { display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; }
    .digest-list { margin:10px 0 0; color:var(--muted); padding-left:18px; }
    @media (max-width:980px) { header,.toolbar,.grid,.cards { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <div class="pill"><span class="status-dot"></span><span id="platform-status">Mission Control online</span></div>
        <h1>Mission Control</h1>
        <p class="lede">A daily operating surface for agents, approvals, vitals, and the overnight digest. The dashboard is read-first: it observes, explains, and routes approvals without executing actions.</p>
      </div>
      <div class="pill">local-only / reverse-proxy protected</div>
    </header>
    <div class="toolbar">
      <div class="search"><strong>Search</strong> commands, agents, approvals, and traces will land here soon.</div>
      <div class="meta"><span id="stream-state">connecting</span><span class="reconnecting" id="reconnect-state" hidden>reconnecting</span></div>
    </div>
    <section class="grid">
      <div class="panel"><h2>Live Activity</h2><div id="feed"></div></div>
      <div class="panel"><h2>Approvals</h2><div id="approvals"></div></div>
    </section>
    <section class="panel" style="margin-top:14px;"><h2>Vitals</h2><div class="cards" id="vitals"></div></section>
    <section class="panel digest">
      <div class="digest-bar"><h3>Overnight Digest</h3><a href="api/events" style="color:var(--accent);text-decoration:none;">Replay events</a></div>
      <div id="digest" class="muted">Loading digest?</div>
    </section>
  </div>
  <script>
    const state = { events: [], approvals: [], digest: null, vitals: null, eventSource: null };
    const els = { feed: document.getElementById('feed'), approvals: document.getElementById('approvals'), vitals: document.getElementById('vitals'), digest: document.getElementById('digest'), streamState: document.getElementById('stream-state'), reconnectState: document.getElementById('reconnect-state') };
    function riskClass(risk) { return risk === 'high' ? 'pill-high' : risk === 'medium' ? 'pill-medium' : 'pill-low'; }
    function formatTs(ts) { return new Date(ts).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); }
    function renderFeed() { els.feed.innerHTML = state.events.map((event) => { const trace = event.trace || {}; const links = (event.links || []).map((link) => `<a href="${link.href}" target="_blank" rel="noreferrer">${link.label}</a>`).join(' ? '); return `
      <div class="feed-item"><div class="feed-head"><div><div class="feed-title">${event.title}</div><div class="feed-meta">${event.agent} ? ${event.kind} ? ${formatTs(event.ts)}</div></div>${event.risk ? `<span class="pill-mini ${riskClass(event.risk)}">${event.risk}</span>` : ''}</div>${event.detail ? `<div class="muted">${event.detail}</div>` : ''}<details><summary>Why this happened</summary><div class="trace"><div><strong>Trigger:</strong> ${trace.trigger || 'n/a'}</div><div><strong>Policy:</strong> ${trace.policy || 'n/a'}</div><div><strong>Steps:</strong> ${(trace.steps || []).join(' ? ') || 'n/a'}</div><div><strong>Outcome:</strong> ${trace.outcome || 'n/a'}</div>${links ? `<div><strong>Links:</strong> ${links}</div>` : ''}</div></details></div>`; }).join('') || '<p class="muted">No events yet.</p>'; }
    async function resolveApproval(id, action) { const approval = state.approvals.find((item) => item.id === id); if (approval && approval.risk !== 'low' && !window.confirm(`This is a ${approval.risk} approval. Confirm ${action}?`)) return; const response = await fetch(`api/approvals/${id}/${action}?confirm=true`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ resolver: 'human' }) }); if (!response.ok) return; await refreshApprovals(); await refreshEvents(); }
    function renderApprovals() { els.approvals.innerHTML = state.approvals.map((approval) => `<article class="card"><h3>${approval.title}</h3><div class="muted">${approval.requested_by} ? ${approval.risk || 'unspecified'} ? ${approval.rollback_available ? 'rollback available' : 'no rollback'}</div><p>${approval.summary || ''}</p>${approval.diff_ref ? `<a href="${approval.diff_ref}" target="_blank" rel="noreferrer">diff / artifact</a>` : ''}<div class="approval-actions"><button class="primary" onclick="window.__mcResolve('${approval.id}', 'approve')">Approve</button><button class="danger" onclick="window.__mcResolve('${approval.id}', 'reject')">Reject</button></div></article>`).join('') || '<p class="muted">No pending approvals.</p>'; }
    function renderVitals() { const vitals = state.vitals || {}; const containerHealth = `${vitals.containers_healthy ?? 0}/${vitals.containers_total ?? 0} healthy`; els.vitals.innerHTML = [['CPU', vitals.cpu_percent == null ? 'n/a' : `${vitals.cpu_percent.toFixed(1)}%`], ['Temp', vitals.soc_temp_c == null ? 'n/a' : `${vitals.soc_temp_c.toFixed(1)} ?C`], ['Throttle', vitals.throttle_state || 'unknown'], ['RAM', vitals.ram_percent == null ? 'n/a' : `${vitals.ram_percent.toFixed(1)}%`], ['Disk', vitals.disk_percent == null ? 'n/a' : `${vitals.disk_percent.toFixed(1)}%`], ['Containers', containerHealth]].map(([label, value]) => `<article class="card"><h3>${label}</h3><div class="kpi">${value}</div></article>`).join(''); }
    function renderDigest() { if (!state.digest) return; const d = state.digest; const tasks = d.tasks ?? 0; const autoFixes = d.auto_fixes ?? 0; const prsOpened = d.prs_opened ?? 0; const pendingApprovals = d.pending_approvals ?? 0; const failures = d.failures ?? 0; const notableEvents = Array.isArray(d.notable_events) ? d.notable_events : []; els.digest.innerHTML = `<div>${tasks} tasks, ${autoFixes} auto-fixes, ${prsOpened} PRs opened, ${pendingApprovals} approvals waiting, ${failures} failures</div><ul class="digest-list">${notableEvents.map((event) => `<li>${event.title || 'Untitled event'} - ${event.agent || 'unknown'}</li>`).join('')}</ul>`; }
    async function refreshEvents() { const response = await fetch('api/events?limit=30'); const data = await response.json(); state.events = data.items || []; renderFeed(); }
    async function refreshApprovals() { const response = await fetch('api/approvals?status=pending'); const data = await response.json(); state.approvals = data.items || []; renderApprovals(); }
    async function refreshVitals() { const response = await fetch('api/vitals'); state.vitals = await response.json(); renderVitals(); }
    async function refreshDigest() { const response = await fetch('api/digest'); state.digest = await response.json(); renderDigest(); }
    function connectStream() { if (state.eventSource) state.eventSource.close(); els.streamState.textContent = 'connecting'; els.reconnectState.hidden = true; const source = new EventSource('api/stream'); state.eventSource = source; source.onopen = () => { els.streamState.textContent = 'live'; els.reconnectState.hidden = true; }; source.addEventListener('refresh', () => refreshEvents()); source.onerror = () => { els.streamState.textContent = 'live'; els.reconnectState.hidden = false; }; }
    window.__mcResolve = (id, action) => resolveApproval(id, action);
    async function boot() { await Promise.all([refreshEvents(), refreshApprovals(), refreshVitals(), refreshDigest()]); connectStream(); setInterval(refreshVitals, 10000); setInterval(refreshApprovals, 15000); setInterval(refreshDigest, 30000); }
    boot();
  </script>
</body>
</html>"""
