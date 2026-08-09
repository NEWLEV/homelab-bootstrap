'use strict';

/* Aisha chat client.
 *
 * Talks only to the same-origin chat gateway (services/openclaw/server.js),
 * which holds the Local RAG credentials server-side. All assistant output is
 * rendered through DOM text nodes; no HTML from the model is ever injected.
 */

(() => {
  const API_BASE = window.location.pathname.startsWith('/aisha')
    ? '/aisha/api'
    : '/api';

  const MAX_QUESTION_LENGTH = 2000;
  const HEALTH_BACKOFF_MS = [5000, 10000, 30000];

  const embedded = window.parent !== window;

  const el = {
    app: document.getElementById('aisha-app'),
    statusLine: document.getElementById('aisha-status-text'),
    statusLabel: document.getElementById('status-label'),
    picker: document.getElementById('conversation-picker'),
    newConversation: document.getElementById('new-conversation'),
    deleteConversation: document.getElementById('delete-conversation'),
    minimize: document.getElementById('minimize-chat'),
    close: document.getElementById('close-chat'),
    notice: document.getElementById('notice'),
    noticeText: document.getElementById('notice-text'),
    noticeRetry: document.getElementById('notice-retry'),
    scroll: document.getElementById('message-scroll'),
    list: document.getElementById('message-list'),
    emptyState: document.getElementById('empty-state'),
    jumpLatest: document.getElementById('jump-latest'),
    liveRegion: document.getElementById('live-region'),
    composer: document.getElementById('composer'),
    input: document.getElementById('composer-input'),
    send: document.getElementById('send-button'),
    stop: document.getElementById('stop-button'),
  };

  // Origins the embedding dashboard may message from. Starts with our own
  // origin; extended with the gateway-configured embed origins from /api/health.
  const allowedParentOrigins = new Set([window.location.origin]);
  const initialParentOrigin = (() => {
    if (!embedded || !document.referrer) {
      return null;
    }
    try {
      return new URL(document.referrer).origin;
    } catch {
      return null;
    }
  })();
  let parentOrigin = initialParentOrigin;


  function createClientMessageId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }
    if (window.crypto && typeof window.crypto.getRandomValues === 'function') {
      const bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 0x0f) | 0x40;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'));
      return `${hex.slice(0, 4).join('')}-${hex.slice(4, 6).join('')}-${hex.slice(6, 8).join('')}-${hex.slice(8, 10).join('')}-${hex.slice(10, 16).join('')}`;
    }
    return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  const state = {
    conversationId: null,
    conversations: [],
    sending: false,
    abortController: null,
    health: null,
    healthAttempt: 0,
    healthTimer: null,
    rateLimitTimer: null,
    panelVisible: !embedded,
    lastFailedSend: null,
  };

  /* ---------- utilities ---------- */

  function announce(text) {
    el.liveRegion.textContent = '';
    window.setTimeout(() => {
      el.liveRegion.textContent = text;
    }, 30);
  }

  function draftKey() {
    return `aisha:draft:${state.conversationId || 'new'}`;
  }

  function saveDraft() {
    try {
      const value = el.input.value;
      if (value) {
        window.localStorage.setItem(draftKey(), value);
      } else {
        window.localStorage.removeItem(draftKey());
      }
    } catch {
      /* Storage may be unavailable; drafts then live only in the field. */
    }
  }

  function restoreDraft() {
    try {
      el.input.value = window.localStorage.getItem(draftKey()) || '';
    } catch {
      /* ignore */
    }
    updateSendState();
  }

  function clearDraft() {
    try {
      window.localStorage.removeItem(draftKey());
    } catch {
      /* ignore */
    }
  }

  function isNearBottom() {
    const { scrollTop, scrollHeight, clientHeight } = el.scroll;
    return scrollHeight - scrollTop - clientHeight < 80;
  }

  function scrollToBottom() {
    el.scroll.scrollTop = el.scroll.scrollHeight;
    el.jumpLatest.hidden = true;
  }

  function maybeScroll(wasNearBottom) {
    if (wasNearBottom) {
      scrollToBottom();
    } else {
      el.jumpLatest.hidden = false;
    }
  }

  /* ---------- safe rendering ---------- */

  const CITATION_PATTERN = /\[([^:\]\n]+):(\d+)-(\d+)\]/g;

  function appendTextWithCitations(parent, text) {
    let lastIndex = 0;
    CITATION_PATTERN.lastIndex = 0;
    let match;
    while ((match = CITATION_PATTERN.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parent.appendChild(
          document.createTextNode(text.slice(lastIndex, match.index)),
        );
      }
      const chip = document.createElement('span');
      chip.className = 'citation-chip';
      chip.textContent = `${match[1]}:${match[2]}-${match[3]}`;
      parent.appendChild(chip);
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      parent.appendChild(document.createTextNode(text.slice(lastIndex)));
    }
  }

  function appendInline(parent, text, withCitations) {
    const parts = text.split(/`([^`\n]+)`/);
    for (let i = 0; i < parts.length; i += 1) {
      if (!parts[i]) {
        continue;
      }
      if (i % 2 === 1) {
        const code = document.createElement('code');
        code.textContent = parts[i];
        parent.appendChild(code);
      } else if (withCitations) {
        appendTextWithCitations(parent, parts[i]);
      } else {
        parent.appendChild(document.createTextNode(parts[i]));
      }
    }
  }

  function renderRichText(container, text, withCitations) {
    container.textContent = '';
    const lines = String(text).split('\n');
    let index = 0;

    while (index < lines.length) {
      const line = lines[index];

      if (line.trimStart().startsWith('```')) {
        const codeLines = [];
        index += 1;
        while (index < lines.length && !lines[index].trimStart().startsWith('```')) {
          codeLines.push(lines[index]);
          index += 1;
        }
        index += 1;
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = codeLines.join('\n');
        pre.appendChild(code);
        container.appendChild(pre);
        continue;
      }

      if (/^\s*[-*]\s+/.test(line)) {
        const listElement = document.createElement('ul');
        while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
          const item = document.createElement('li');
          appendInline(item, lines[index].replace(/^\s*[-*]\s+/, ''), withCitations);
          listElement.appendChild(item);
          index += 1;
        }
        container.appendChild(listElement);
        continue;
      }

      const paragraphLines = [];
      while (
        index < lines.length &&
        lines[index].trim() !== '' &&
        !lines[index].trimStart().startsWith('```') &&
        !/^\s*[-*]\s+/.test(lines[index])
      ) {
        paragraphLines.push(lines[index]);
        index += 1;
      }
      if (paragraphLines.length > 0) {
        const paragraph = document.createElement('p');
        paragraphLines.forEach((paragraphLine, lineIndex) => {
          if (lineIndex > 0) {
            paragraph.appendChild(document.createElement('br'));
          }
          appendInline(paragraph, paragraphLine, withCitations);
        });
        container.appendChild(paragraph);
      } else {
        index += 1;
      }
    }
  }

  /* ---------- message rendering ---------- */

  function messageElement(role) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const meta = document.createElement('div');
    meta.className = 'meta';
    const name = document.createElement('span');
    name.textContent = role === 'user' ? 'You' : 'Aisha';
    meta.appendChild(name);

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    wrapper.appendChild(meta);
    wrapper.appendChild(bubble);
    return { wrapper, meta, bubble };
  }

  function addBadge(meta, kind, label) {
    const badge = document.createElement('span');
    badge.className = `badge ${kind}`;
    badge.textContent = label;
    meta.appendChild(badge);
  }

  function addCopyButton(wrapper, text) {
    if (!navigator.clipboard) {
      return;
    }
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'copy-button';
    button.textContent = 'Copy';
    button.setAttribute('aria-label', 'Copy Aisha’s response');
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = 'Copied';
        announce('Response copied to clipboard.');
        window.setTimeout(() => {
          button.textContent = 'Copy';
        }, 2000);
      } catch {
        announce('Copy failed.');
      }
    });
    actions.appendChild(button);
    wrapper.appendChild(actions);
  }

  function renderAssistantMessage(message) {
    const { wrapper, meta, bubble } = messageElement('assistant');
    renderRichText(bubble, message.content, true);

    if (message.status === 'stopped') {
      addBadge(meta, 'stopped', 'Stopped');
    } else if (message.grounded) {
      addBadge(meta, 'grounded', 'Grounded');
    }

    if (Array.isArray(message.citations) && message.citations.length > 0) {
      const citations = document.createElement('div');
      for (const citation of message.citations) {
        const chip = document.createElement('span');
        chip.className = 'citation-chip';
        chip.textContent =
          `${citation.path}:${citation.line_start}-${citation.line_end}`;
        citations.appendChild(chip);
      }
      bubble.appendChild(citations);
    }

    addCopyButton(wrapper, message.content);
    el.list.appendChild(wrapper);
    return wrapper;
  }

  function renderUserMessage(message) {
    const { wrapper, bubble } = messageElement('user');
    renderRichText(bubble, message.content, false);
    el.list.appendChild(wrapper);
    return wrapper;
  }

  function renderConversation(messages) {
    el.list.textContent = '';
    for (const message of messages) {
      if (message.role === 'user') {
        renderUserMessage(message);
      } else {
        renderAssistantMessage(message);
      }
    }
    el.emptyState.hidden = messages.length > 0;
    scrollToBottom();
  }

  /* ---------- status handling ---------- */

  function setStatus(stateName, label) {
    el.statusLine.dataset.state = stateName;
    el.statusLabel.textContent = label;
    updateSendState();
  }

  function serviceAvailable() {
    return Boolean(state.health && state.health.ready) && navigator.onLine;
  }

  function updateSendState() {
    const hasText = el.input.value.trim().length > 0;
    const rateLimited = Boolean(state.rateLimitTimer);
    el.send.disabled =
      !hasText || state.sending || rateLimited || !serviceAvailable();
  }

  function describeHealth(health) {
    if (!health) {
      return { state: 'error', label: 'Status unknown' };
    }
    if (health.ready) {
      return { state: 'ok', label: 'Connected' };
    }
    const upstream = health.knowledge_service || {};
    if (!upstream.reachable) {
      return { state: 'degraded', label: 'Knowledge service unreachable' };
    }
    if (upstream.authentication_enabled && !health.knowledge_service_token_configured) {
      return { state: 'degraded', label: 'Gateway authorization not configured' };
    }
    return { state: 'degraded', label: 'Service degraded' };
  }

  async function checkHealth() {
    if (state.healthTimer) {
      window.clearTimeout(state.healthTimer);
      state.healthTimer = null;
    }

    if (!navigator.onLine) {
      setStatus('offline', 'You are offline');
      return;
    }

    let health = null;
    try {
      const response = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
      if (response.ok) {
        health = await response.json();
      }
    } catch {
      health = null;
    }

    if (health && Array.isArray(health.embed_origins)) {
      for (const origin of health.embed_origins) {
        allowedParentOrigins.add(origin);
      }
      if (initialParentOrigin && allowedParentOrigins.has(initialParentOrigin)) {
        parentOrigin = initialParentOrigin;
      }
    }

    const previouslyReady = Boolean(state.health && state.health.ready);
    state.health = health;
    const described = describeHealth(health);
    setStatus(described.state, described.label);

    if (health && health.ready) {
      state.healthAttempt = 0;
      if (!previouslyReady) {
        announce('Aisha is connected.');
      }
      if (embedded) {
        postToParent({ type: 'aisha:status', available: true });
      }
      return;
    }

    if (embedded) {
      postToParent({ type: 'aisha:status', available: false });
    }

    // Reconnect probing with bounded backoff while the panel is visible.
    if (state.panelVisible && !document.hidden) {
      const delay =
        HEALTH_BACKOFF_MS[
          Math.min(state.healthAttempt, HEALTH_BACKOFF_MS.length - 1)
        ];
      state.healthAttempt += 1;
      state.healthTimer = window.setTimeout(checkHealth, delay);
    }
  }

  /* ---------- notices ---------- */

  function showNotice(kind, text, retryHandler) {
    el.notice.hidden = false;
    el.notice.dataset.kind = kind;
    el.noticeText.textContent = text;
    if (retryHandler) {
      el.noticeRetry.hidden = false;
      el.noticeRetry.onclick = () => {
        hideNotice();
        retryHandler();
      };
    } else {
      el.noticeRetry.hidden = true;
      el.noticeRetry.onclick = null;
    }
    announce(text);
  }

  function hideNotice() {
    el.notice.hidden = true;
  }

  function startRateLimitCountdown(seconds) {
    let remaining = Math.max(1, seconds);
    const update = () => {
      if (remaining <= 0) {
        window.clearInterval(state.rateLimitTimer);
        state.rateLimitTimer = null;
        hideNotice();
        updateSendState();
        return;
      }
      showNotice(
        'warn',
        `Rate limit reached. You can send again in ${remaining}s.`,
        null,
      );
      remaining -= 1;
    };
    if (state.rateLimitTimer) {
      window.clearInterval(state.rateLimitTimer);
    }
    update();
    state.rateLimitTimer = window.setInterval(update, 1000);
    updateSendState();
  }

  /* ---------- conversations ---------- */

  async function apiJson(pathname, options) {
    const response = await fetch(`${API_BASE}${pathname}`, options);
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    return { response, payload };
  }

  function populatePicker() {
    el.picker.textContent = '';
    if (state.conversations.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'New conversation';
      el.picker.appendChild(option);
      return;
    }
    for (const conversation of state.conversations) {
      const option = document.createElement('option');
      option.value = conversation.id;
      option.textContent = conversation.title || 'Untitled conversation';
      if (conversation.id === state.conversationId) {
        option.selected = true;
      }
      el.picker.appendChild(option);
    }
  }

  async function refreshConversations() {
    try {
      const { response, payload } = await apiJson('/conversations');
      if (response.ok && payload && Array.isArray(payload.conversations)) {
        state.conversations = payload.conversations;
        populatePicker();
      }
    } catch {
      /* listing is best-effort; sending still validates against the server */
    }
  }

  async function loadConversation(conversationId) {
    saveDraft();
    state.conversationId = conversationId;
    hideNotice();

    if (!conversationId) {
      renderConversation([]);
      restoreDraft();
      return;
    }

    try {
      const { response, payload } = await apiJson(`/conversations/${conversationId}`);
      if (response.ok && payload) {
        renderConversation(payload.messages || []);
      } else {
        state.conversationId = null;
        renderConversation([]);
        showNotice('error', 'That conversation could not be loaded.', null);
      }
    } catch {
      showNotice(
        'error',
        'Could not load the conversation history. Check the connection and retry.',
        () => loadConversation(conversationId),
      );
    }
    restoreDraft();
  }

  async function ensureConversation() {
    if (state.conversationId) {
      return state.conversationId;
    }
    const { response, payload } = await apiJson('/conversations', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{}',
    });
    if (!response.ok || !payload || !payload.id) {
      throw new Error(
        (payload && payload.detail) || 'Could not create a conversation.',
      );
    }
    state.conversationId = payload.id;
    await refreshConversations();
    return payload.id;
  }

  async function deleteCurrentConversation() {
    if (!state.conversationId || state.sending) {
      return;
    }
    const confirmed = window.confirm(
      'Delete this conversation permanently? This cannot be undone.',
    );
    if (!confirmed) {
      return;
    }
    const conversationId = state.conversationId;
    const { response, payload } = await apiJson(`/conversations/${conversationId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      showNotice(
        'error',
        (payload && payload.detail) || 'The conversation could not be deleted.',
        null,
      );
      return;
    }
    announce('Conversation deleted.');
    state.conversationId = null;
    await refreshConversations();
    const next = state.conversations[0];
    await loadConversation(next ? next.id : null);
  }

  /* ---------- sending ---------- */

  function parseSse(onEvent) {
    let buffer = '';
    return (chunk) => {
      buffer += chunk;
      let separator;
      while ((separator = buffer.indexOf('\n\n')) !== -1) {
        const record = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        let eventName = 'message';
        const dataLines = [];
        for (const line of record.split('\n')) {
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trimStart());
          }
        }
        if (dataLines.length === 0) {
          continue;
        }
        try {
          onEvent(eventName, JSON.parse(dataLines.join('\n')));
        } catch {
          /* skip malformed record */
        }
      }
    };
  }

  function friendlySendError(status, detail) {
    if (status === 429) {
      return detail || 'Rate limit reached. Try again shortly.';
    }
    if (status === 503) {
      return (
        detail ||
        'Aisha is temporarily unavailable. Try again shortly.'
      );
    }
    if (status === 502) {
      return (
        detail ||
        'The knowledge service is unreachable. Check the local-rag service.'
      );
    }
    if (status === 422 || status === 409) {
      return detail || 'The message could not be accepted.';
    }
    return detail || 'Sending failed. Check the connection and retry.';
  }

  async function sendQuestion(question, clientMessageId) {
    hideNotice();
    state.sending = true;
    state.lastFailedSend = null;
    updateSendState();
    el.stop.hidden = false;
    el.input.disabled = false;

    const wasNearBottom = isNearBottom();
    const userNode = renderUserMessage({ role: 'user', content: question });
    el.emptyState.hidden = true;

    const streaming = messageElement('assistant');
    streaming.wrapper.classList.add('provisional');
    const indicator = document.createElement('span');
    indicator.className = 'streaming-indicator';
    indicator.textContent = 'Aisha is responding…';
    streaming.meta.appendChild(indicator);
    el.list.appendChild(streaming.wrapper);
    maybeScroll(wasNearBottom);

    announce('Aisha is responding.');

    const controller = new AbortController();
    state.abortController = controller;

    let streamedText = '';
    let finalPayload = null;
    let streamErrorDetail = null;

    const applyEvent = (eventName, payload) => {
      if (eventName === 'token' && typeof payload.text === 'string') {
        const nearBottom = isNearBottom();
        streamedText += payload.text;
        streaming.bubble.textContent = streamedText;
        maybeScroll(nearBottom);
      } else if (eventName === 'result') {
        finalPayload = payload;
      } else if (eventName === 'error') {
        streamErrorDetail = payload.detail || 'Generation failed.';
      }
    };

    const failSend = (message, allowRetry) => {
      streaming.wrapper.remove();
      userNode.remove();
      el.input.value = question;
      saveDraft();
      updateSendState();
      if (allowRetry) {
        state.lastFailedSend = { question, clientMessageId };
        showNotice('error', message, () => {
          el.input.value = '';
          clearDraft();
          sendQuestion(question, clientMessageId);
        });
      } else {
        showNotice('error', message, null);
      }
    };

    try {
      const conversationId = await ensureConversation();
      const response = await fetch(
        `${API_BASE}/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          headers: {
            'content-type': 'application/json',
            accept: 'text/event-stream',
          },
          body: JSON.stringify({
            question,
            client_message_id: clientMessageId,
          }),
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        let detail = null;
        try {
          const payload = await response.json();
          detail = payload && payload.detail;
        } catch {
          detail = null;
        }
        if (response.status === 429) {
          const retryAfter = Number.parseInt(
            response.headers.get('retry-after') || '30',
            10,
          );
          streaming.wrapper.remove();
          userNode.remove();
          el.input.value = question;
          saveDraft();
          startRateLimitCountdown(
            Number.isNaN(retryAfter) ? 30 : retryAfter,
          );
          return;
        }
        failSend(friendlySendError(response.status, detail), true);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const feed = parseSse(applyEvent);

      for (;;) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        feed(decoder.decode(value, { stream: true }));
        if (streamErrorDetail || finalPayload) {
          if (finalPayload) {
            continue;
          }
          break;
        }
      }

      if (streamErrorDetail) {
        failSend(friendlySendError(500, streamErrorDetail), true);
        return;
      }

      if (!finalPayload) {
        failSend(
          'The response stream ended unexpectedly. Retry to continue.',
          true,
        );
        return;
      }

      streaming.wrapper.remove();
      const nearBottom = isNearBottom();
      renderAssistantMessage({
        role: 'assistant',
        content: finalPayload.answer,
        grounded: finalPayload.grounded,
        citations: finalPayload.citations,
        status: 'complete',
      });
      maybeScroll(nearBottom);
      clearDraft();
      announce('Aisha replied.');
      if (embedded && (!state.panelVisible || document.hidden)) {
        postToParent({ type: 'aisha:activity' });
      }
      refreshConversations();
    } catch (error) {
      if (controller.signal.aborted) {
        // User pressed stop: keep the partial text, mark it clearly.
        if (streamedText) {
          streaming.wrapper.classList.remove('provisional');
          addBadge(streaming.meta, 'stopped', 'Stopped');
          const indicatorNode = streaming.meta.querySelector('.streaming-indicator');
          if (indicatorNode) {
            indicatorNode.remove();
          }
          state.lastFailedSend = { question, clientMessageId };
          showNotice(
            'warn',
            'Generation stopped. The partial answer is not verified.',
            () => {
              streaming.wrapper.remove();
              userNode.remove();
              sendQuestion(question, clientMessageId);
            },
          );
        } else {
          streaming.wrapper.remove();
          userNode.remove();
          el.input.value = question;
          saveDraft();
          announce('Generation stopped.');
        }
      } else if (!navigator.onLine) {
        failSend('You are offline. Reconnect and retry.', true);
        checkHealth();
      } else {
        failSend(
          'The connection was interrupted. Retry to continue — retries are safe and will not duplicate your message.',
          true,
        );
        checkHealth();
      }
    } finally {
      state.sending = false;
      state.abortController = null;
      el.stop.hidden = true;
      updateSendState();
      el.input.focus();
    }
  }

  function submitComposer() {
    const question = el.input.value.trim();
    if (!question || state.sending || state.rateLimitTimer) {
      return;
    }
    if (!serviceAvailable()) {
      showNotice(
        'error',
        'Aisha is unavailable right now. The connection will be retried automatically.',
        null,
      );
      checkHealth();
      return;
    }
    if (question.length > MAX_QUESTION_LENGTH) {
      showNotice(
        'error',
        `Messages are limited to ${MAX_QUESTION_LENGTH} characters.`,
        null,
      );
      return;
    }
    el.input.value = '';
    clearDraft();
    autoresize();
    sendQuestion(question, createClientMessageId());
  }

  /* ---------- composer behavior ---------- */

  function autoresize() {
    el.input.style.height = 'auto';
    el.input.style.height = `${Math.min(el.input.scrollHeight, 160)}px`;
  }

  el.input.addEventListener('input', () => {
    saveDraft();
    updateSendState();
    autoresize();
  });

  el.input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitComposer();
    }
  });

  el.composer.addEventListener('submit', (event) => {
    event.preventDefault();
    submitComposer();
  });

  el.stop.addEventListener('click', () => {
    if (state.abortController) {
      state.abortController.abort();
    }
  });

  /* ---------- header actions ---------- */

  el.newConversation.addEventListener('click', async () => {
    if (state.sending) {
      return;
    }
    saveDraft();
    state.conversationId = null;
    renderConversation([]);
    restoreDraft();
    populatePicker();
    el.input.focus();
  });

  el.deleteConversation.addEventListener('click', deleteCurrentConversation);

  el.picker.addEventListener('change', () => {
    if (state.sending) {
      populatePicker();
      return;
    }
    loadConversation(el.picker.value || null);
  });

  el.jumpLatest.addEventListener('click', () => {
    scrollToBottom();
  });

  el.scroll.addEventListener('scroll', () => {
    if (isNearBottom()) {
      el.jumpLatest.hidden = true;
    }
  });

  for (const suggestion of document.querySelectorAll('.suggestion')) {
    suggestion.addEventListener('click', () => {
      el.input.value = suggestion.dataset.question || suggestion.textContent;
      updateSendState();
      el.input.focus();
    });
  }

  /* ---------- embedding protocol ---------- */

  function postToParent(message) {
    const targetOrigin =
      parentOrigin && allowedParentOrigins.has(parentOrigin)
        ? parentOrigin
        : initialParentOrigin && allowedParentOrigins.has(initialParentOrigin)
          ? initialParentOrigin
          : null;
    if (!targetOrigin) {
      return;
    }
    window.parent.postMessage(message, targetOrigin);
  }

  if (embedded) {
    document.body.classList.add('embedded');
    el.minimize.addEventListener('click', () => postToParent({ type: 'aisha:minimize' }));
    el.close.addEventListener('click', () => postToParent({ type: 'aisha:close' }));

    window.addEventListener('message', (event) => {
      if (!allowedParentOrigins.has(event.origin) || !event.data) {
        return;
      }
      parentOrigin = event.origin;
      if (event.data.type === 'aisha:opened') {
        state.panelVisible = true;
        el.input.focus();
        checkHealth();
      } else if (event.data.type === 'aisha:visibility') {
        state.panelVisible = Boolean(event.data.visible);
        if (state.panelVisible) {
          checkHealth();
        }
      }
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && embedded) {
      // Closing hides the panel; an active stream keeps running and is
      // persisted by the gateway, so nothing is silently discarded.
      postToParent({ type: 'aisha:close' });
    }
  });

  /* ---------- connectivity ---------- */

  window.addEventListener('online', () => {
    announce('Back online. Reconnecting to Aisha.');
    checkHealth();
  });
  window.addEventListener('offline', () => {
    setStatus('offline', 'You are offline');
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      checkHealth();
    }
  });

  /* ---------- start ---------- */

  async function start() {
    setStatus('connecting', 'Connecting…');
    await checkHealth();
    await refreshConversations();
    const latest = state.conversations[0];
    await loadConversation(latest ? latest.id : null);
    if (!embedded) {
      el.input.focus();
    }
  }

  start();
})();
