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

  const QUICK_GROUPS = [
    {
      title: 'Assistant Runtimes',
      accent: 'secure',
      intro: 'The primary surfaces for conversation, control, and autonomous work.',
      links: [
        { label: 'OpenClaw', href: 'https://aisha.tail4553c9.ts.net/openclaw/', note: 'Control UI' },
        { label: 'Hermes', href: 'http://aisha:9119/', note: 'Assistant runtime' },
      ],
    },
    {
      title: 'Automation & Ops',
      accent: 'local',
      intro: 'Workflow automation, monitoring, and the live homelab consoles.',
      links: [
        { label: 'n8n', href: 'https://aisha.tail4553c9.ts.net/n8n/home/workflows', note: 'Automation' },
        { label: 'Kuma', href: 'http://100.106.201.14:3001', note: 'Uptime Kuma' },
        { label: 'File Browser', href: 'http://100.106.201.14:8080', note: 'Files' },
        { label: 'Portainer', href: 'http://100.106.201.14:9000', note: 'Containers' },
        { label: 'Netdata', href: 'http://100.106.201.14:19999', note: 'Metrics' },
        { label: 'Pironman5 Max', href: 'http://aisha:34001', note: 'Hardware telemetry' },
      ],
    },
  ];

  const PORT_LINKS = [
    { label: '3001', href: 'http://100.106.201.14:3001', title: 'Kuma' },
    { label: '8080', href: 'http://100.106.201.14:8080', title: 'File Browser' },
    { label: '9000', href: 'http://100.106.201.14:9000', title: 'Portainer' },
    { label: '19999', href: 'http://100.106.201.14:19999', title: 'Netdata' },
    { label: '34001', href: 'http://aisha:34001', title: 'Pironman5 Max' },
  ];

  // The gateway is intentionally reachable only through the same-origin,
  // tailnet-restricted Traefik route at /aisha. It has no host-published
  // fallback port.
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

    const shell = document.createElement('div');
    shell.className = 'aisha-quick-links-shell';

    const masthead = document.createElement('div');
    masthead.className = 'aisha-quick-links-masthead';

    const heading = document.createElement('div');
    heading.className = 'aisha-quick-links-heading';
    heading.textContent = 'Aisha Control Center';
    masthead.appendChild(heading);

    const tagline = document.createElement('p');
    tagline.className = 'aisha-quick-links-intro';
    tagline.textContent = 'Fast access to OpenClaw, Hermes, n8n, and the live homelab surfaces.';
    masthead.appendChild(tagline);

    const badgeRow = document.createElement('div');
    badgeRow.className = 'aisha-quick-links-badges';
    for (const badge of ['secure', 'tailnet', 'local', 'observability']) {
      const chip = document.createElement('span');
      chip.className = 'aisha-quick-links-badge';
      chip.textContent = badge;
      badgeRow.appendChild(chip);
    }
    masthead.appendChild(badgeRow);
    shell.appendChild(masthead);

    const grid = document.createElement('div');
    grid.className = 'aisha-quick-links-grid';

    for (const group of QUICK_GROUPS) {
      const card = document.createElement('article');
      card.className = 'aisha-quick-links-card';

      const cardHeader = document.createElement('div');
      cardHeader.className = 'aisha-quick-links-card-header';

      const cardTitle = document.createElement('h3');
      cardTitle.textContent = group.title;
      cardHeader.appendChild(cardTitle);

      const cardAccent = document.createElement('span');
      cardAccent.className = 'aisha-quick-links-accent';
      cardAccent.textContent = group.accent;
      cardHeader.appendChild(cardAccent);
      card.appendChild(cardHeader);

      const cardIntro = document.createElement('p');
      cardIntro.className = 'aisha-quick-links-card-intro';
      cardIntro.textContent = group.intro;
      card.appendChild(cardIntro);

      const list = document.createElement('div');
      list.className = 'aisha-quick-links-list';

      for (const item of group.links) {
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

      card.appendChild(list);
      grid.appendChild(card);
    }

    shell.appendChild(grid);
    panel.appendChild(shell);

    const ports = document.createElement('section');
    ports.className = 'aisha-port-links';

    const portsHeading = document.createElement('h3');
    portsHeading.textContent = 'Ports';
    ports.appendChild(portsHeading);

    const portsIntro = document.createElement('p');
    portsIntro.className = 'aisha-port-links-intro';
    portsIntro.textContent = 'Quick access to the live service ports.';
    ports.appendChild(portsIntro);

    const portsRow = document.createElement('div');
    portsRow.className = 'aisha-port-links-row';

    for (const item of PORT_LINKS) {
      const port = document.createElement('a');
      port.className = 'aisha-port-link';
      port.href = item.href;
      port.title = `${item.title} (${item.label})`;
      port.target = item.href.startsWith('/') ? '_self' : '_blank';
      port.rel = port.target === '_blank' ? 'noreferrer noopener' : '';
      port.textContent = item.label;
      portsRow.appendChild(port);
    }

    ports.appendChild(portsRow);
    panel.appendChild(ports);


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
    const quickLinks = createQuickLinksPanel();
    const dashboardRoot = document.querySelector('.wrap') || document.querySelector('main') || document.body;
    const dashboardHero = dashboardRoot.querySelector('.hero') || dashboardRoot.querySelector('[class*="hero"]');
    quickLinks.classList.add(dashboardHero ? 'aisha-quick-links-inline' : 'aisha-quick-links-floating');
    if (dashboardHero) {
      dashboardHero.insertAdjacentElement('afterend', quickLinks);
    } else {
      dashboardRoot.prepend(quickLinks);
    }
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
