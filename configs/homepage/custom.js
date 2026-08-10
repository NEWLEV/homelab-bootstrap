'use strict';

/* Aisha chat launcher for the Homepage dashboard.
 *
 * Installed at /srv/data/services/homepage/config/custom.js (see
 * scripts/install-homepage-aisha-launcher). The chat itself is served
 * same-origin by the OpenClaw gateway under /aisha/ and proxied to the
 * Local RAG service; no credentials ever reach this file or the browser.
 */

(() => {
  if (window.__aishaLauncher) {
    return;
  }
  window.__aishaLauncher = true;

  const STATE_KEY = 'aisha:panel-state';
  const UNREAD_KEY = 'aisha:unread';
  const PROBE_INTERVAL_MS = 60000;

  const QUICK_LINKS = [
    { label: 'OpenClaw', href: 'https://aisha.tail4553c9.ts.net/openclaw/', note: 'Control UI' },
    { label: 'Mission Control', href: '/platform/web-dashboard#mission-control', note: 'coming soon' },
    { label: 'Kuma', href: 'http://100.106.201.14:3001', note: 'Uptime Kuma' },
    { label: 'File Browser', href: 'http://100.106.201.14:8080', note: 'Files' },
    { label: 'Portainer', href: 'https://100.106.201.14:9443', note: 'Containers' },
    { label: 'Netdata', href: 'http://100.106.201.14:19999', note: 'Metrics' },
    { label: 'Pironman5 Max', href: '/platform/web-dashboard#pironman5', note: 'coming soon' },
  ];

  // The gateway is intentionally reachable only through the same-origin,
  // tailnet-restricted Traefik route. It has no host-published fallback port.
  const CHAT_BASES = [
    { base: '/aisha', origin: window.location.origin },
  ];

  let available = false;
  let chatBase = null;
  let chatOrigin = null;
  let panel = null;
  let iframe = null;
  let probeTimer = null;

  const button = document.createElement('button');
  button.type = 'button';
  button.id = 'aisha-launcher';
  button.setAttribute('aria-label', 'Chat with Aisha');
  button.setAttribute('aria-haspopup', 'dialog');
  button.setAttribute('aria-expanded', 'false');
  button.title = 'Chat with Aisha';
  button.dataset.state = 'loading';

  const glyph = document.createElement('span');
  glyph.className = 'aisha-launcher-glyph';
  glyph.setAttribute('aria-hidden', 'true');
  glyph.textContent = 'A';
  button.appendChild(glyph);

  const unreadDot = document.createElement('span');
  unreadDot.className = 'aisha-unread-dot';
  unreadDot.hidden = true;
  button.appendChild(unreadDot);

  const srUnread = document.createElement('span');
  srUnread.className = 'aisha-visually-hidden';
  srUnread.textContent = '';
  button.appendChild(srUnread);


  function createQuickLinksPanel() {
    const panel = document.createElement('section');
    panel.id = 'aisha-quick-links';
    panel.setAttribute('aria-label', 'Aisha dashboard shortcuts');

    const heading = document.createElement('h2');
    heading.textContent = 'Aisha Control Center';
    panel.appendChild(heading);

    const intro = document.createElement('p');
    intro.className = 'aisha-quick-links-intro';
    intro.textContent = 'Open the secure OpenClaw UI, the chat surface, or the homelab tools below. Mission Control and Pi dashboard features are marked coming soon until their standalone pages are ready.';
    panel.appendChild(intro);

    const list = document.createElement('div');
    list.className = 'aisha-quick-links-list';

    for (const item of QUICK_LINKS) {
      const link = document.createElement('a');
      link.className = 'aisha-quick-link';
      link.href = item.href;
      link.target = item.href.startsWith('/') ? '_self' : '_blank';
      link.rel = link.target === '_blank' ? 'noreferrer noopener' : '';

      const title = document.createElement('span');
      title.className = 'aisha-quick-link-title';
      title.textContent = item.label;
      link.appendChild(title);

      const note = document.createElement('span');
      note.className = 'aisha-quick-link-note';
      note.textContent = item.note;
      link.appendChild(note);

      list.appendChild(link);
    }

    panel.appendChild(list);

    const mission = document.createElement('section');
    mission.id = 'mission-control';
    mission.className = 'aisha-coming-soon';
    const missionTitle = document.createElement('h3');
    missionTitle.textContent = 'Mission Control';
    const missionBody = document.createElement('p');
    missionBody.textContent = 'Coming soon: approvals, live activity, vitals, and replay will live here once the standalone page is ready.';
    mission.appendChild(missionTitle);
    mission.appendChild(missionBody);
    panel.appendChild(mission);

    const pironman = document.createElement('section');
    pironman.id = 'pironman5';
    pironman.className = 'aisha-coming-soon';
    const pironmanTitle = document.createElement('h3');
    pironmanTitle.textContent = 'Pironman5 Max';
    const pironmanBody = document.createElement('p');
    pironmanBody.textContent = 'Coming soon: hardware telemetry and control will live here after the Pi dashboard is verified live.';
    pironman.appendChild(pironmanTitle);
    pironman.appendChild(pironmanBody);
    panel.appendChild(pironman);

    return panel;
  }

  function readState(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function writeState(key, value) {
    try {
      if (value === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch {
      /* ignore storage failures */
    }
  }

  function setUnread(flag) {
    unreadDot.hidden = !flag;
    srUnread.textContent = flag ? ' (new reply from Aisha)' : '';
    writeState(UNREAD_KEY, flag ? '1' : null);
  }

  function setAvailability(isAvailable) {
    available = isAvailable;
    if (isAvailable) {
      button.dataset.state = 'ready';
      button.removeAttribute('aria-disabled');
      button.title = 'Chat with Aisha';
    } else {
      button.dataset.state = 'unavailable';
      button.setAttribute('aria-disabled', 'true');
      button.title = 'Aisha is currently unavailable';
    }
  }

  async function probeAvailability() {
    for (const candidate of CHAT_BASES) {
      try {
        const response = await fetch(`${candidate.base}/api/health`, {
          cache: 'no-store',
        });
        if (!response.ok) {
          continue;
        }
        const payload = await response.json();
        // The panel keeps a live iframe with chat state; once a base is
        // chosen it stays chosen so the conversation is not torn down.
        if (!chatBase) {
          chatBase = candidate.base;
          chatOrigin = candidate.origin;
        }
        if (candidate.base === chatBase) {
          setAvailability(Boolean(payload && payload.ready));
          return;
        }
      } catch {
        // Try the next candidate base.
      }
    }
    setAvailability(false);
  }

  function scheduleProbes() {
    if (probeTimer) {
      window.clearInterval(probeTimer);
    }
    probeTimer = window.setInterval(() => {
      if (!available || (panel && !panel.hidden)) {
        probeAvailability();
      }
    }, PROBE_INTERVAL_MS);
  }

  function ensurePanel() {
    if (panel) {
      return;
    }
    panel = document.createElement('div');
    panel.id = 'aisha-panel';
    panel.hidden = true;

    iframe = document.createElement('iframe');
    iframe.id = 'aisha-frame';
    iframe.src = `${chatBase}/`;
    iframe.title = 'Aisha chat';
    panel.appendChild(iframe);
    document.body.appendChild(panel);
  }

  function notifyFrame(message) {
    if (iframe && iframe.contentWindow && chatOrigin) {
      iframe.contentWindow.postMessage(message, chatOrigin);
    }
  }

  function openPanel() {
    if (!chatBase) {
      return;
    }
    ensurePanel();
    panel.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    button.classList.add('aisha-open');
    setUnread(false);
    writeState(STATE_KEY, 'open');
    notifyFrame({ type: 'aisha:visibility', visible: true });
    // Give the frame a tick to render before moving focus into it.
    window.setTimeout(() => {
      iframe.focus();
      notifyFrame({ type: 'aisha:opened' });
    }, 60);
  }

  function hidePanel(nextState) {
    if (!panel || panel.hidden) {
      return;
    }
    panel.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    button.classList.remove('aisha-open');
    writeState(STATE_KEY, nextState);
    notifyFrame({ type: 'aisha:visibility', visible: false });
    button.focus();
  }

  button.addEventListener('click', () => {
    if (!available) {
      // Re-probe on demand so a recovered service becomes usable immediately.
      probeAvailability();
      return;
    }
    if (panel && !panel.hidden) {
      hidePanel('closed');
    } else {
      openPanel();
    }
  });

  window.addEventListener('message', (event) => {
    if (event.origin !== chatOrigin || !event.data) {
      return;
    }
    const { type } = event.data;
    if (type === 'aisha:close') {
      hidePanel('closed');
    } else if (type === 'aisha:minimize') {
      hidePanel('minimized');
    } else if (type === 'aisha:activity') {
      if (!panel || panel.hidden) {
        setUnread(true);
      }
    } else if (type === 'aisha:status') {
      setAvailability(Boolean(event.data.available));
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && panel && !panel.hidden) {
      hidePanel('closed');
    }
  });

  function start() {
    document.body.appendChild(createQuickLinksPanel());
    document.body.appendChild(button);
    setUnread(readState(UNREAD_KEY) === '1');
    probeAvailability().then(() => {
      // Restore panel state across dashboard navigation.
      if (available && readState(STATE_KEY) === 'open') {
        openPanel();
      }
    });
    scheduleProbes();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
