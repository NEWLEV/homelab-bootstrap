#!/usr/bin/env node
'use strict';

const http = require('node:http');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

const GATEWAY_VERSION = '0.1.0';

const DEFAULT_UI_DIR = fs.existsSync('/usr/local/share/openclaw-ui')
  ? '/usr/local/share/openclaw-ui'
  : path.join(__dirname, 'ui');

// Origins allowed to embed the chat UI and probe /api/health cross-origin
// (the dashboard, when it is served from a different origin than this
// gateway). Same-origin embedding is always allowed.
function parseEmbedOrigins(value) {
  return (value || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => /^https?:\/\/[^/\s]+$/.test(entry));
}

const config = {
  configDir: process.env.OPENCLAW_CONFIG_DIR || '/config',
  stateDir: process.env.OPENCLAW_STATE_DIR || '/state',
  secretsFile: process.env.OPENCLAW_SECRETS_FILE || '/run/secrets/openclaw_env',
  localRagUrl: process.env.OPENCLAW_LOCAL_RAG_URL || 'http://local-rag-api:8080',
  localRagTokenFile:
    process.env.OPENCLAW_LOCAL_RAG_TOKEN_FILE || '/run/secrets/local_rag_api_token',
  gatewayBind: process.env.OPENCLAW_GATEWAY_BIND || '127.0.0.1',
  gatewayPort: Number.parseInt(process.env.OPENCLAW_GATEWAY_PORT || '18789', 10),
  embedOrigins: parseEmbedOrigins(process.env.OPENCLAW_EMBED_ORIGINS),
  uiDir: process.env.OPENCLAW_UI_DIR || DEFAULT_UI_DIR,
  nodeCompileCache: process.env.NODE_COMPILE_CACHE || '/var/tmp/openclaw-compile-cache',
  noRespawn: process.env.OPENCLAW_NO_RESPAWN || '1',
};

const conversationsDir = path.join(config.stateDir, 'conversations');

// Mirrors the Local RAG AskRequest contract (services/local-rag/app/main.py).
const MAX_QUESTION_LENGTH = 2000;
const MAX_HISTORY_MESSAGES = 8;
const MAX_REQUEST_BODY_BYTES = 16 * 1024;
const MAX_CONVERSATIONS = 500;
const MAX_MESSAGES_PER_CONVERSATION = 400;
const CONVERSATION_LIST_LIMIT = 50;
const UPSTREAM_HEALTH_TIMEOUT_MS = 5000;
const UPSTREAM_STREAM_TIMEOUT_MS = 300000;

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const STATIC_FILES = new Map([
  ['/', { file: 'index.html', type: 'text/html; charset=utf-8' }],
  ['/index.html', { file: 'index.html', type: 'text/html; charset=utf-8' }],
  ['/app.js', { file: 'app.js', type: 'text/javascript; charset=utf-8' }],
  ['/styles.css', { file: 'styles.css', type: 'text/css; charset=utf-8' }],
]);

const FRAME_ANCESTORS = ["'self'", ...config.embedOrigins].join(' ');

const UI_SECURITY_HEADERS = {
  'content-security-policy':
    "default-src 'self'; img-src 'self' data:; style-src 'self'; " +
    "script-src 'self'; connect-src 'self'; " +
    `frame-ancestors ${FRAME_ANCESTORS}; ` +
    "base-uri 'none'; form-action 'self'",
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'no-referrer',
};

// Serialized writers so concurrent requests never interleave conversation writes.
const conversationLocks = new Map();

// In-flight generation keyed by `${conversationId}:${clientMessageId}`.
const activeGenerations = new Set();

function withConversationLock(conversationId, task) {
  const previous = conversationLocks.get(conversationId) || Promise.resolve();
  const next = previous.then(task, task);
  conversationLocks.set(
    conversationId,
    next.catch(() => {}),
  );
  next.finally(() => {
    if (conversationLocks.get(conversationId) === next) {
      conversationLocks.delete(conversationId);
    }
  }).catch(() => {});
  return next;
}

function loadLocalRagToken() {
  let raw;
  try {
    raw = fs.readFileSync(config.localRagTokenFile, 'utf8');
  } catch {
    return null;
  }

  const token = raw.trim();
  if (!token || token.length < 32 || /\s/.test(token)) {
    return null;
  }
  return token;
}

function isValidUuid(value) {
  return typeof value === 'string' && UUID_PATTERN.test(value);
}

function conversationPath(conversationId) {
  return path.join(conversationsDir, `${conversationId}.json`);
}

async function readConversation(conversationId) {
  try {
    const raw = await fsp.readFile(conversationPath(conversationId), 'utf8');
    const conversation = JSON.parse(raw);
    if (!conversation || conversation.id !== conversationId) {
      return null;
    }
    if (!Array.isArray(conversation.messages)) {
      conversation.messages = [];
    }
    return conversation;
  } catch {
    return null;
  }
}

async function writeConversation(conversation) {
  await fsp.mkdir(conversationsDir, { recursive: true });
  const target = conversationPath(conversation.id);
  const temporary = path.join(
    conversationsDir,
    `.${conversation.id}.${crypto.randomBytes(6).toString('hex')}.tmp`,
  );

  await fsp.writeFile(temporary, JSON.stringify(conversation), 'utf8');
  await fsp.rename(temporary, target);
}

function conversationSummary(conversation) {
  return {
    id: conversation.id,
    title: conversation.title,
    created_at: conversation.created_at,
    updated_at: conversation.updated_at,
    message_count: conversation.messages.length,
  };
}

async function listConversationSummaries() {
  let entries;
  try {
    entries = await fsp.readdir(conversationsDir);
  } catch {
    return [];
  }

  const summaries = [];
  for (const entry of entries) {
    if (!entry.endsWith('.json')) {
      continue;
    }
    const conversationId = entry.slice(0, -'.json'.length);
    if (!isValidUuid(conversationId)) {
      continue;
    }
    const conversation = await readConversation(conversationId);
    if (conversation) {
      summaries.push(conversationSummary(conversation));
    }
  }

  summaries.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
  return summaries.slice(0, CONVERSATION_LIST_LIMIT);
}

async function countConversations() {
  try {
    const entries = await fsp.readdir(conversationsDir);
    return entries.filter((entry) => entry.endsWith('.json')).length;
  } catch {
    return 0;
  }
}

function buildHistory(conversation, beforeMessageId) {
  const history = [];
  for (const message of conversation.messages) {
    if (message.id === beforeMessageId) {
      break;
    }
    if (message.role === 'assistant' && message.status !== 'complete') {
      continue;
    }
    const content = String(message.content || '').slice(0, MAX_QUESTION_LENGTH);
    if (!content.trim()) {
      continue;
    }
    history.push({ role: message.role, content });
  }
  return history.slice(-MAX_HISTORY_MESSAGES);
}

function sendJson(res, statusCode, payload, extraHeaders = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store',
    ...UI_SECURITY_HEADERS,
    ...extraHeaders,
  });
  res.end(body);
}

function sseEvent(event, payload) {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function readRequestBody(req, res) {
  return new Promise((resolve) => {
    const chunks = [];
    let received = 0;
    let finished = false;

    const finish = (value) => {
      if (!finished) {
        finished = true;
        resolve(value);
      }
    };

    req.on('data', (chunk) => {
      received += chunk.length;
      if (received > MAX_REQUEST_BODY_BYTES) {
        sendJson(res, 413, { detail: 'Request body is too large.' });
        req.destroy();
        finish(null);
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => finish(Buffer.concat(chunks).toString('utf8')));
    req.on('error', () => finish(null));
  });
}

function parseJsonBody(raw, res) {
  if (raw === null) {
    return undefined;
  }
  if (!raw.trim()) {
    return {};
  }
  try {
    const parsed = JSON.parse(raw);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      sendJson(res, 422, { detail: 'Request body must be a JSON object.' });
      return undefined;
    }
    return parsed;
  } catch {
    sendJson(res, 422, { detail: 'Request body must be valid JSON.' });
    return undefined;
  }
}

async function fetchUpstreamHealth() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), UPSTREAM_HEALTH_TIMEOUT_MS);

  try {
    const response = await fetch(`${config.localRagUrl}/health`, {
      signal: controller.signal,
    });
    if (!response.ok) {
      return { reachable: false, status: 'error', http_status: response.status };
    }
    const payload = await response.json();
    return {
      reachable: true,
      status: String(payload.status || 'unknown'),
      version: payload.version,
      chunks: payload.chunks,
      embedding_model: payload.embedding_model,
      generation_model: payload.generation_model,
      index_status: payload.index_status,
      authentication_enabled: Boolean(payload.authentication_enabled),
      rate_limiting_enabled: Boolean(payload.rate_limiting_enabled),
    };
  } catch {
    return { reachable: false, status: 'unreachable' };
  } finally {
    clearTimeout(timer);
  }
}

async function handleApiHealth(req, res) {
  const upstream = await fetchUpstreamHealth();
  const tokenConfigured = loadLocalRagToken() !== null;
  const authorizationReady =
    upstream.reachable && (!upstream.authentication_enabled || tokenConfigured);
  const ready = upstream.reachable && upstream.status === 'ok' && authorizationReady;

  // The dashboard launcher may probe health from an allowlisted embedding
  // origin. Health is the only endpoint with CORS; chat traffic itself is
  // always same-origin inside the embedded frame.
  const corsHeaders = { vary: 'Origin' };
  const requestOrigin = req.headers.origin;
  if (requestOrigin && config.embedOrigins.includes(requestOrigin)) {
    corsHeaders['access-control-allow-origin'] = requestOrigin;
  }

  sendJson(
    res,
    200,
    {
      status: ready ? 'ok' : 'degraded',
      service: 'aisha-chat-gateway',
      version: GATEWAY_VERSION,
      knowledge_service: upstream,
      knowledge_service_token_configured: tokenConfigured,
      embed_origins: config.embedOrigins,
      ready,
    },
    corsHeaders,
  );
}

async function handleListConversations(res) {
  const conversations = await listConversationSummaries();
  sendJson(res, 200, { conversations });
}

async function handleCreateConversation(res) {
  const total = await countConversations();
  if (total >= MAX_CONVERSATIONS) {
    sendJson(res, 507, {
      detail:
        'Conversation limit reached. Delete old conversations before creating new ones.',
    });
    return;
  }

  const now = new Date().toISOString();
  const conversation = {
    id: crypto.randomUUID(),
    title: 'New conversation',
    created_at: now,
    updated_at: now,
    messages: [],
  };

  await withConversationLock(conversation.id, () => writeConversation(conversation));
  sendJson(res, 201, conversationSummary(conversation));
}

async function handleGetConversation(res, conversationId) {
  const conversation = await readConversation(conversationId);
  if (!conversation) {
    sendJson(res, 404, { detail: 'Conversation not found.' });
    return;
  }
  sendJson(res, 200, conversation);
}

async function handleDeleteConversation(res, conversationId) {
  const removed = await withConversationLock(conversationId, async () => {
    try {
      await fsp.unlink(conversationPath(conversationId));
      return true;
    } catch {
      return false;
    }
  });

  if (!removed) {
    sendJson(res, 404, { detail: 'Conversation not found.' });
    return;
  }
  sendJson(res, 200, { deleted: conversationId });
}

function mapUpstreamFailure(statusCode, detail, retryAfter) {
  if (statusCode === 401 || statusCode === 403) {
    return {
      status: 503,
      detail:
        'The gateway is not authorized with the local knowledge service. ' +
        'Verify the Local RAG API token secret and restart the gateway.',
    };
  }
  if (statusCode === 429) {
    return {
      status: 429,
      detail: 'The knowledge service is rate limiting requests. Try again shortly.',
      retryAfter: retryAfter || '30',
    };
  }
  if (statusCode === 503) {
    return {
      status: 503,
      detail: 'The knowledge service is busy. Try again shortly.',
      retryAfter: retryAfter || '5',
    };
  }
  if (statusCode === 413 || statusCode === 422) {
    return {
      status: statusCode,
      detail: detail || 'The knowledge service rejected the request.',
    };
  }
  return {
    status: 502,
    detail: 'The knowledge service returned an unexpected error.',
  };
}

async function parseUpstreamErrorDetail(response) {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === 'string') {
      return payload.detail;
    }
  } catch {
    // Ignore unparseable upstream error bodies.
  }
  return null;
}

// Incremental parser for the Local RAG SSE stream (event:/data: records).
function createSseParser(onEvent) {
  let buffer = '';

  return (chunk) => {
    buffer += chunk;
    let separatorIndex;
    while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
      const record = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      let eventName = 'message';
      const dataLines = [];
      for (const line of record.split('\n')) {
        if (line.startsWith('event:')) {
          eventName = line.slice('event:'.length).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice('data:'.length).trimStart());
        }
      }

      if (dataLines.length === 0) {
        continue;
      }
      let payload;
      try {
        payload = JSON.parse(dataLines.join('\n'));
      } catch {
        continue;
      }
      onEvent(eventName, payload);
    }
  };
}

function findReply(conversation, clientMessageId) {
  return conversation.messages.find(
    (message) =>
      message.role === 'assistant' && message.in_reply_to === clientMessageId,
  );
}

async function handleSendMessage(req, res, conversationId, body) {
  const question =
    typeof body.question === 'string' ? body.question.trim() : '';
  const clientMessageId = body.client_message_id;

  if (!question) {
    sendJson(res, 422, { detail: 'Question must not be empty.' });
    return;
  }
  if (question.length > MAX_QUESTION_LENGTH) {
    sendJson(res, 422, {
      detail: `Question must be at most ${MAX_QUESTION_LENGTH} characters.`,
    });
    return;
  }
  if (!isValidUuid(clientMessageId)) {
    sendJson(res, 422, {
      detail: 'client_message_id must be a UUID for idempotent retries.',
    });
    return;
  }

  const generationKey = `${conversationId}:${clientMessageId}`;
  if (activeGenerations.has(generationKey)) {
    sendJson(res, 409, {
      detail: 'This message is already being processed.',
    });
    return;
  }

  const token = loadLocalRagToken();
  if (token === null) {
    sendJson(res, 503, {
      detail:
        'The Local RAG API token is not configured for the gateway. ' +
        'Run scripts/local-rag-token on the host and restart the OpenClaw service.',
    });
    return;
  }

  let userMessage = null;
  let replayReply = null;
  let history = [];

  const prepared = await withConversationLock(conversationId, async () => {
    const conversation = await readConversation(conversationId);
    if (!conversation) {
      return { error: { status: 404, detail: 'Conversation not found.' } };
    }

    const existing = conversation.messages.find(
      (message) =>
        message.role === 'user' && message.client_message_id === clientMessageId,
    );

    if (existing) {
      const reply = findReply(conversation, clientMessageId);
      if (reply && reply.status === 'complete') {
        replayReply = { conversation, userMessage: existing, reply };
        return {};
      }
      // Retry of a failed or stopped attempt: drop the stale partial reply.
      conversation.messages = conversation.messages.filter(
        (message) =>
          !(
            message.role === 'assistant' &&
            message.in_reply_to === clientMessageId &&
            message.status !== 'complete'
          ),
      );
      userMessage = existing;
    } else {
      if (conversation.messages.length >= MAX_MESSAGES_PER_CONVERSATION) {
        return {
          error: {
            status: 409,
            detail: 'This conversation is full. Start a new conversation.',
          },
        };
      }
      userMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
        client_message_id: clientMessageId,
        created_at: new Date().toISOString(),
      };
      conversation.messages.push(userMessage);
      if (conversation.messages.length === 1) {
        conversation.title = question.slice(0, 80);
      }
    }

    conversation.updated_at = new Date().toISOString();
    history = buildHistory(conversation, userMessage.id);
    await writeConversation(conversation);
    return {};
  });

  if (prepared && prepared.error) {
    sendJson(res, prepared.error.status, { detail: prepared.error.detail });
    return;
  }

  if (replayReply) {
    res.writeHead(200, {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache',
      'x-accel-buffering': 'no',
      ...UI_SECURITY_HEADERS,
    });
    res.write(
      sseEvent('result', {
        conversation_id: conversationId,
        message_id: replayReply.reply.id,
        replayed: true,
        question: replayReply.userMessage.content,
        answer: replayReply.reply.content,
        grounded: Boolean(replayReply.reply.grounded),
        citations: replayReply.reply.citations || [],
        confidence: replayReply.reply.confidence ?? 0,
      }),
    );
    res.end();
    return;
  }

  activeGenerations.add(generationKey);
  const upstreamController = new AbortController();
  const upstreamTimer = setTimeout(
    () => upstreamController.abort(),
    UPSTREAM_STREAM_TIMEOUT_MS,
  );

  let clientClosed = false;
  const collectedTokens = [];
  let finalized = false;

  const persistReply = (reply) =>
    withConversationLock(conversationId, async () => {
      const conversation = await readConversation(conversationId);
      if (!conversation) {
        return;
      }
      conversation.messages = conversation.messages.filter(
        (message) =>
          !(
            message.role === 'assistant' &&
            message.in_reply_to === clientMessageId
          ),
      );
      conversation.messages.push(reply);
      conversation.updated_at = new Date().toISOString();
      await writeConversation(conversation);
    });

  const finishStoppedPartial = async () => {
    if (finalized) {
      return;
    }
    finalized = true;
    const partial = collectedTokens.join('').trim();
    if (partial) {
      await persistReply({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: partial,
        in_reply_to: clientMessageId,
        created_at: new Date().toISOString(),
        status: 'stopped',
        grounded: false,
        citations: [],
      });
    }
  };

  res.on('close', () => {
    clientClosed = true;
    if (!res.writableEnded) {
      upstreamController.abort();
    }
  });

  try {
    let upstream;
    try {
      upstream = await fetch(`${config.localRagUrl}/ask/stream`, {
        method: 'POST',
        headers: {
          authorization: `Bearer ${token}`,
          'content-type': 'application/json',
          accept: 'text/event-stream',
        },
        body: JSON.stringify({ question, history, limit: 5 }),
        signal: upstreamController.signal,
      });
    } catch {
      if (!clientClosed) {
        sendJson(res, 502, {
          detail:
            'The local knowledge service is unreachable. ' +
            'Check that the local-rag containers are running, then retry.',
        });
      }
      return;
    }

    if (!upstream.ok) {
      const detail = await parseUpstreamErrorDetail(upstream);
      const mapped = mapUpstreamFailure(
        upstream.status,
        detail,
        upstream.headers.get('retry-after'),
      );
      if (!clientClosed) {
        const headers = mapped.retryAfter
          ? { 'retry-after': mapped.retryAfter }
          : {};
        sendJson(res, mapped.status, { detail: mapped.detail }, headers);
      }
      return;
    }

    res.writeHead(200, {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache',
      'x-accel-buffering': 'no',
      ...UI_SECURITY_HEADERS,
    });
    res.write(
      sseEvent('accepted', {
        conversation_id: conversationId,
        user_message_id: userMessage.id,
      }),
    );

    let streamError = null;
    let finalResult = null;

    const parse = createSseParser((eventName, payload) => {
      if (eventName === 'token' && typeof payload.text === 'string') {
        collectedTokens.push(payload.text);
        if (!clientClosed) {
          res.write(sseEvent('token', { text: payload.text }));
        }
      } else if (eventName === 'result') {
        finalResult = payload;
      } else if (eventName === 'error') {
        streamError = typeof payload.detail === 'string'
          ? payload.detail
          : 'The knowledge service reported a generation error.';
      }
    });

    const decoder = new TextDecoder();
    try {
      for await (const chunk of upstream.body) {
        parse(decoder.decode(chunk, { stream: true }));
        if (streamError) {
          break;
        }
      }
    } catch {
      if (clientClosed) {
        await finishStoppedPartial();
        return;
      }
      streamError = 'The connection to the knowledge service was interrupted.';
    }

    if (streamError) {
      finalized = true;
      if (!clientClosed) {
        res.write(sseEvent('error', { detail: streamError }));
        res.end();
      }
      return;
    }

    if (!finalResult) {
      if (clientClosed) {
        await finishStoppedPartial();
        return;
      }
      finalized = true;
      res.write(
        sseEvent('error', {
          detail: 'The knowledge service ended the stream without a result.',
        }),
      );
      res.end();
      return;
    }

    finalized = true;
    const reply = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: String(finalResult.answer || ''),
      in_reply_to: clientMessageId,
      created_at: new Date().toISOString(),
      status: 'complete',
      grounded: Boolean(finalResult.grounded),
      citations: Array.isArray(finalResult.citations) ? finalResult.citations : [],
      confidence:
        typeof finalResult.confidence === 'number' ? finalResult.confidence : 0,
    };
    await persistReply(reply);

    if (!clientClosed) {
      res.write(
        sseEvent('result', {
          conversation_id: conversationId,
          message_id: reply.id,
          question,
          answer: reply.content,
          grounded: reply.grounded,
          citations: reply.citations,
          confidence: reply.confidence,
        }),
      );
      res.end();
    }
  } finally {
    clearTimeout(upstreamTimer);
    activeGenerations.delete(generationKey);
    if (clientClosed && !finalized) {
      await finishStoppedPartial();
    }
  }
}

function serveStatic(res, pathname) {
  const entry = STATIC_FILES.get(pathname);
  if (!entry) {
    return false;
  }

  let content;
  try {
    content = fs.readFileSync(path.join(config.uiDir, entry.file));
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('not found\n');
    return true;
  }

  res.writeHead(200, {
    'content-type': entry.type,
    'content-length': content.length,
    'cache-control': 'no-cache',
    ...UI_SECURITY_HEADERS,
  });
  res.end(content);
  return true;
}

async function route(req, res) {
  const url = new URL(req.url, 'http://gateway.internal');
  let pathname = url.pathname;

  // Traefik routes the dashboard-facing surface under /aisha without stripping.
  const prefixed = pathname === '/aisha' || pathname.startsWith('/aisha/');
  if (prefixed) {
    pathname = pathname.slice('/aisha'.length) || '/';
  }

  if (!prefixed && pathname === '/health') {
    const body = JSON.stringify({
      status: 'ok',
      gatewayBind: config.gatewayBind,
      gatewayPort: config.gatewayPort,
      localRagUrl: config.localRagUrl,
      secretsFile: config.secretsFile,
      stateDir: config.stateDir,
      configDir: config.configDir,
    });
    res.writeHead(200, {
      'content-type': 'application/json; charset=utf-8',
      'content-length': Buffer.byteLength(body),
    });
    res.end(body);
    return;
  }

  if (!prefixed && pathname === '/ready') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('openclaw ready\n');
    return;
  }

  if (pathname === '/api/health') {
    if (req.method !== 'GET') {
      sendJson(res, 405, { detail: 'Method not allowed.' });
      return;
    }
    await handleApiHealth(req, res);
    return;
  }

  if (pathname === '/api/conversations') {
    if (req.method === 'GET') {
      await handleListConversations(res);
      return;
    }
    if (req.method === 'POST') {
      await handleCreateConversation(res);
      return;
    }
    sendJson(res, 405, { detail: 'Method not allowed.' });
    return;
  }

  const conversationMatch = pathname.match(
    /^\/api\/conversations\/([^/]+)(\/messages)?$/,
  );
  if (conversationMatch) {
    const conversationId = conversationMatch[1];
    const isMessages = Boolean(conversationMatch[2]);

    if (!isValidUuid(conversationId)) {
      sendJson(res, 404, { detail: 'Conversation not found.' });
      return;
    }

    if (isMessages) {
      if (req.method !== 'POST') {
        sendJson(res, 405, { detail: 'Method not allowed.' });
        return;
      }
      const raw = await readRequestBody(req, res);
      const body = parseJsonBody(raw, res);
      if (body === undefined) {
        return;
      }
      await handleSendMessage(req, res, conversationId, body);
      return;
    }

    if (req.method === 'GET') {
      await handleGetConversation(res, conversationId);
      return;
    }
    if (req.method === 'DELETE') {
      await handleDeleteConversation(res, conversationId);
      return;
    }
    sendJson(res, 405, { detail: 'Method not allowed.' });
    return;
  }

  if (req.method === 'GET' && serveStatic(res, pathname)) {
    return;
  }

  res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('not found\n');
}

const server = http.createServer((req, res) => {
  route(req, res).catch((error) => {
    process.stderr.write(`Unhandled gateway error: ${error.message}\n`);
    if (!res.headersSent) {
      sendJson(res, 500, { detail: 'Internal gateway error.' });
    } else if (!res.writableEnded) {
      res.end();
    }
  });
});

fs.mkdirSync(conversationsDir, { recursive: true });

if (require.main === module) {
  server.listen(config.gatewayPort, config.gatewayBind, () => {
    process.stdout.write(
      `OpenClaw runtime ready on ${config.gatewayBind}:${config.gatewayPort}\n`,
    );
    if (loadLocalRagToken() === null) {
      process.stderr.write(
        'Aisha chat gateway: Local RAG API token is not configured; ' +
        `chat requests will be refused until ${config.localRagTokenFile} is present.\n`,
      );
    }
  });

  process.on('SIGTERM', () => server.close(() => process.exit(0)));
  process.on('SIGINT', () => server.close(() => process.exit(0)));
}

module.exports = { server, config };
