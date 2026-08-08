'use strict';

/* Integration tests for the Aisha chat gateway.
 *
 * The gateway is exercised over real HTTP against a stub that implements the
 * Local RAG API contract (bearer auth, /health, and the /ask/stream SSE
 * event shapes from services/local-rag/app/main.py). Model inference cannot
 * run in CI, so this is the integration boundary; the Local RAG side of the
 * same contract is covered by its own pytest suite.
 */

const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const TEST_TOKEN = 'a'.repeat(64);

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'aisha-gateway-test-'));
const stateDir = path.join(tmpRoot, 'state');
const tokenFile = path.join(tmpRoot, 'local-rag-token');

let stubServer;
let stubPort;
let gatewayServer;
let gatewayPort;

const stubState = {
  lastAuthorization: null,
  slowRequestClosed: false,
  releaseSlow: null,
};

function sse(event, payload) {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function stubHandler(req, res) {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(
      JSON.stringify({
        status: 'ok',
        version: '0.11.0',
        chunks: 42,
        embedding_model: 'nomic-embed-text',
        generation_model: 'llama3.2:3b',
        index_status: 'succeeded',
        authentication_enabled: true,
        rate_limiting_enabled: true,
      }),
    );
    return;
  }

  if (req.url === '/ask/stream' && req.method === 'POST') {
    stubState.lastAuthorization = req.headers.authorization || null;

    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      const request = JSON.parse(body);
      const question = request.question;

      if (stubState.lastAuthorization !== `Bearer ${TEST_TOKEN}`) {
        res.writeHead(401, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ detail: 'Authentication required.' }));
        return;
      }

      if (question.includes('TRIGGER_RATE_LIMIT')) {
        res.writeHead(429, {
          'content-type': 'application/json',
          'retry-after': '7',
        });
        res.end(JSON.stringify({ detail: 'Rate limit exceeded.' }));
        return;
      }

      if (question.includes('TRIGGER_AUTH')) {
        res.writeHead(401, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ detail: 'Authentication required.' }));
        return;
      }

      const sseHeaders = {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
      };

      if (question.includes('TRIGGER_ERROR_EVENT')) {
        res.writeHead(200, sseHeaders);
        res.write(sse('error', { detail: 'Ollama generation failed: boom' }));
        res.end();
        return;
      }

      if (question.includes('TRIGGER_SLOW')) {
        res.writeHead(200, sseHeaders);
        res.write(sse('token', { text: 'partial ' }));
        stubState.slowRequestClosed = false;
        req.on('close', () => {
          stubState.slowRequestClosed = true;
        });
        // Held open until the test releases it or the gateway aborts.
        stubState.releaseSlow = () => {
          res.write(
            sse('result', {
              question,
              answer: 'slow answer [docs/network.md:1-5]',
              grounded: true,
              citations: [
                {
                  path: 'docs/network.md',
                  line_start: 1,
                  line_end: 5,
                  distance: 0.2,
                },
              ],
              confidence: 0.8,
            }),
          );
          res.end();
        };
        return;
      }

      res.writeHead(200, sseHeaders);
      res.write(sse('token', { text: 'The backup ' }));
      res.write(sse('token', { text: 'runs nightly.' }));
      res.write(
        sse('result', {
          question,
          answer:
            'The backup runs nightly. [configs/systemd/aisha-backup.timer:1-9]',
          grounded: true,
          citations: [
            {
              path: 'configs/systemd/aisha-backup.timer',
              line_start: 1,
              line_end: 9,
              distance: 0.15,
            },
          ],
          confidence: 0.91,
          history_length: Array.isArray(request.history)
            ? request.history.length
            : -1,
        }),
      );
      res.end();
    });
    return;
  }

  res.writeHead(404, { 'content-type': 'application/json' });
  res.end(JSON.stringify({ detail: 'Not found' }));
}

function listen(server, port = 0) {
  return new Promise((resolve, reject) => {
    server.listen(port, '127.0.0.1', () => resolve(server.address().port));
    server.on('error', reject);
  });
}

function gatewayUrl(pathname) {
  return `http://127.0.0.1:${gatewayPort}${pathname}`;
}

async function readSseEvents(response) {
  const text = await response.text();
  const events = [];
  for (const record of text.split('\n\n')) {
    if (!record.trim()) {
      continue;
    }
    let eventName = 'message';
    const dataLines = [];
    for (const line of record.split('\n')) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    if (dataLines.length > 0) {
      events.push({ event: eventName, data: JSON.parse(dataLines.join('\n')) });
    }
  }
  return events;
}

async function createConversation() {
  const response = await fetch(gatewayUrl('/api/conversations'), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: '{}',
  });
  assert.equal(response.status, 201);
  const payload = await response.json();
  assert.ok(payload.id);
  return payload.id;
}

async function sendMessage(conversationId, question, clientMessageId) {
  return fetch(gatewayUrl(`/api/conversations/${conversationId}/messages`), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      question,
      client_message_id: clientMessageId,
    }),
  });
}

async function getConversation(conversationId) {
  const response = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}`),
  );
  assert.equal(response.status, 200);
  return response.json();
}

before(async () => {
  stubServer = http.createServer(stubHandler);
  stubPort = await listen(stubServer);

  fs.mkdirSync(stateDir, { recursive: true });

  process.env.OPENCLAW_STATE_DIR = stateDir;
  process.env.OPENCLAW_LOCAL_RAG_URL = `http://127.0.0.1:${stubPort}`;
  process.env.OPENCLAW_LOCAL_RAG_TOKEN_FILE = tokenFile;
  process.env.OPENCLAW_GATEWAY_BIND = '127.0.0.1';
  process.env.OPENCLAW_EMBED_ORIGINS =
    'http://aisha:8000,http://100.106.201.14:8000,not-an-origin';

  // eslint-disable-next-line global-require
  const gateway = require('../server.js');
  gatewayServer = gateway.server;
  gatewayPort = await listen(gatewayServer);
});

after(async () => {
  await new Promise((resolve) => gatewayServer.close(resolve));
  await new Promise((resolve) => stubServer.close(resolve));
  fs.rmSync(tmpRoot, { recursive: true, force: true });
});

test('legacy runtime endpoints stay on the unprefixed surface', async () => {
  const health = await fetch(gatewayUrl('/health'));
  assert.equal(health.status, 200);
  const payload = await health.json();
  assert.equal(payload.status, 'ok');

  const ready = await fetch(gatewayUrl('/ready'));
  assert.equal(ready.status, 200);

  // The dashboard-facing /aisha prefix must not expose the legacy endpoint.
  const prefixedHealth = await fetch(gatewayUrl('/aisha/health'));
  assert.equal(prefixedHealth.status, 404);
});

test('serves the chat UI with security headers, with and without prefix', async () => {
  for (const pathname of ['/', '/aisha/', '/aisha/app.js', '/styles.css']) {
    const response = await fetch(gatewayUrl(pathname));
    assert.equal(response.status, 200, `expected 200 for ${pathname}`);
    assert.ok(response.headers.get('content-security-policy'));
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  }

  const traversal = await fetch(gatewayUrl('/aisha/..%2Fserver.js'));
  assert.equal(traversal.status, 404);
});

test('allows configured dashboard origins to embed and probe health', async () => {
  // Malformed allowlist entries are dropped; valid origins are kept.
  const page = await fetch(gatewayUrl('/aisha/'));
  const csp = page.headers.get('content-security-policy');
  assert.match(
    csp,
    /frame-ancestors 'self' http:\/\/aisha:8000 http:\/\/100\.106\.201\.14:8000;/,
  );
  assert.ok(!csp.includes('not-an-origin'));

  const allowed = await fetch(gatewayUrl('/api/health'), {
    headers: { origin: 'http://aisha:8000' },
  });
  assert.equal(
    allowed.headers.get('access-control-allow-origin'),
    'http://aisha:8000',
  );
  const payload = await allowed.json();
  assert.deepEqual(payload.embed_origins, [
    'http://aisha:8000',
    'http://100.106.201.14:8000',
  ]);

  const denied = await fetch(gatewayUrl('/api/health'), {
    headers: { origin: 'http://evil.example' },
  });
  assert.equal(denied.headers.get('access-control-allow-origin'), null);

  // Health is the only CORS-enabled endpoint; conversation APIs stay
  // same-origin only.
  const conversations = await fetch(gatewayUrl('/api/conversations'), {
    headers: { origin: 'http://aisha:8000' },
  });
  assert.equal(
    conversations.headers.get('access-control-allow-origin'),
    null,
  );
});

test('api health reports degraded while the token is unconfigured', async () => {
  const response = await fetch(gatewayUrl('/api/health'));
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.status, 'degraded');
  assert.equal(payload.ready, false);
  assert.equal(payload.knowledge_service_token_configured, false);
  assert.equal(payload.knowledge_service.reachable, true);
});

test('message submission is refused with guidance while unconfigured', async () => {
  const conversationId = await createConversation();
  const response = await sendMessage(
    conversationId,
    'How are backups configured?',
    '11111111-1111-4111-8111-111111111111',
  );
  assert.equal(response.status, 503);
  const payload = await response.json();
  assert.match(payload.detail, /local-rag-token/);
});

test('api health becomes ready once the token is provisioned', async () => {
  fs.writeFileSync(tokenFile, `${TEST_TOKEN}\n`);
  const response = await fetch(gatewayUrl('/api/health'));
  const payload = await response.json();
  assert.equal(payload.status, 'ok');
  assert.equal(payload.ready, true);
  assert.equal(payload.knowledge_service_token_configured, true);
  // The health payload must not leak filesystem paths or token material.
  const raw = JSON.stringify(payload);
  assert.ok(!raw.includes(tmpRoot));
  assert.ok(!raw.includes(TEST_TOKEN));
});

test('conversation lifecycle: create, list, fetch, delete', async () => {
  const conversationId = await createConversation();

  const listResponse = await fetch(gatewayUrl('/api/conversations'));
  assert.equal(listResponse.status, 200);
  const listing = await listResponse.json();
  assert.ok(listing.conversations.some((entry) => entry.id === conversationId));

  const conversation = await getConversation(conversationId);
  assert.deepEqual(conversation.messages, []);

  const deleteResponse = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}`),
    { method: 'DELETE' },
  );
  assert.equal(deleteResponse.status, 200);

  const afterDelete = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}`),
  );
  assert.equal(afterDelete.status, 404);
});

test('rejects invalid conversation identifiers', async () => {
  for (const badId of ['..', 'not-a-uuid', '..%2F..%2Fetc']) {
    const response = await fetch(gatewayUrl(`/api/conversations/${badId}`));
    assert.equal(response.status, 404, `expected 404 for ${badId}`);
  }
});

test('validates message submissions', async () => {
  const conversationId = await createConversation();

  const empty = await sendMessage(conversationId, '   ', crypto.randomUUID());
  assert.equal(empty.status, 422);

  const tooLong = await sendMessage(
    conversationId,
    'x'.repeat(2001),
    crypto.randomUUID(),
  );
  assert.equal(tooLong.status, 422);

  const badClientId = await sendMessage(conversationId, 'hello', 'nope');
  assert.equal(badClientId.status, 422);

  const notJson = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}/messages`),
    { method: 'POST', body: 'not json' },
  );
  assert.equal(notJson.status, 422);

  const oversized = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}/messages`),
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        question: 'q',
        client_message_id: crypto.randomUUID(),
        padding: 'p'.repeat(20000),
      }),
    },
  );
  assert.equal(oversized.status, 413);

  const wrongMethod = await fetch(
    gatewayUrl(`/api/conversations/${conversationId}/messages`),
  );
  assert.equal(wrongMethod.status, 405);
});

test('streams a real answer and persists the exchange', async () => {
  const conversationId = await createConversation();
  const clientMessageId = crypto.randomUUID();

  const response = await sendMessage(
    conversationId,
    'How are backups scheduled?',
    clientMessageId,
  );
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /text\/event-stream/);

  const events = await readSseEvents(response);
  const tokens = events.filter((entry) => entry.event === 'token');
  const results = events.filter((entry) => entry.event === 'result');
  assert.equal(tokens.length, 2);
  assert.equal(results.length, 1);
  assert.equal(results[0].data.grounded, true);
  assert.equal(results[0].data.citations.length, 1);
  assert.equal(results[0].data.conversation_id, conversationId);

  // The gateway must have attached the bearer token server-side.
  assert.equal(stubState.lastAuthorization, `Bearer ${TEST_TOKEN}`);

  const conversation = await getConversation(conversationId);
  assert.equal(conversation.messages.length, 2);
  const [userMessage, reply] = conversation.messages;
  assert.equal(userMessage.role, 'user');
  assert.equal(userMessage.client_message_id, clientMessageId);
  assert.equal(reply.role, 'assistant');
  assert.equal(reply.status, 'complete');
  assert.equal(reply.grounded, true);
  assert.equal(conversation.title, 'How are backups scheduled?');
});

test('replays completed answers idempotently instead of regenerating', async () => {
  const conversationId = await createConversation();
  const clientMessageId = crypto.randomUUID();

  const first = await sendMessage(conversationId, 'What runs nightly?', clientMessageId);
  assert.equal(first.status, 200);
  await readSseEvents(first);

  stubState.lastAuthorization = 'unset-by-replay-test';
  const retry = await sendMessage(conversationId, 'What runs nightly?', clientMessageId);
  assert.equal(retry.status, 200);
  const events = await readSseEvents(retry);
  const results = events.filter((entry) => entry.event === 'result');
  assert.equal(results.length, 1);
  assert.equal(results[0].data.replayed, true);

  // No upstream call happened for the replay.
  assert.equal(stubState.lastAuthorization, 'unset-by-replay-test');

  const conversation = await getConversation(conversationId);
  assert.equal(conversation.messages.length, 2);
});

test('sends bounded conversation history on follow-up questions', async () => {
  const conversationId = await createConversation();

  const first = await sendMessage(conversationId, 'First question?', crypto.randomUUID());
  await readSseEvents(first);

  const second = await sendMessage(conversationId, 'Follow up?', crypto.randomUUID());
  const events = await readSseEvents(second);
  const result = events.find((entry) => entry.event === 'result');
  assert.ok(result);

  const conversation = await getConversation(conversationId);
  assert.equal(conversation.messages.length, 4);
});

test('rejects concurrent duplicates of the same message', async () => {
  const conversationId = await createConversation();
  const clientMessageId = crypto.randomUUID();

  const controller = new AbortController();
  const slowPromise = fetch(
    gatewayUrl(`/api/conversations/${conversationId}/messages`),
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        question: 'TRIGGER_SLOW please',
        client_message_id: clientMessageId,
      }),
      signal: controller.signal,
    },
  );

  // Wait for the slow stream to be accepted upstream.
  await new Promise((resolve) => {
    const poll = setInterval(() => {
      if (stubState.releaseSlow) {
        clearInterval(poll);
        resolve();
      }
    }, 20);
  });

  const duplicate = await sendMessage(conversationId, 'TRIGGER_SLOW please', clientMessageId);
  assert.equal(duplicate.status, 409);

  stubState.releaseSlow();
  stubState.releaseSlow = null;
  const original = await slowPromise;
  const events = await readSseEvents(original);
  assert.ok(events.some((entry) => entry.event === 'result'));
});

test('cancellation aborts the upstream stream and keeps a labeled partial', async () => {
  const conversationId = await createConversation();
  const clientMessageId = crypto.randomUUID();

  const controller = new AbortController();
  const pending = fetch(
    gatewayUrl(`/api/conversations/${conversationId}/messages`),
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        question: 'TRIGGER_SLOW cancel me',
        client_message_id: clientMessageId,
      }),
      signal: controller.signal,
    },
  ).catch(() => null);

  await new Promise((resolve) => {
    const poll = setInterval(() => {
      if (stubState.releaseSlow) {
        clearInterval(poll);
        resolve();
      }
    }, 20);
  });

  controller.abort();
  await pending;

  // The gateway aborts its upstream request when the client goes away.
  await new Promise((resolve) => {
    const poll = setInterval(() => {
      if (stubState.slowRequestClosed) {
        clearInterval(poll);
        resolve();
      }
    }, 20);
  });
  stubState.releaseSlow = null;

  // The stopped partial is persisted and marked, ready for a safe retry.
  let conversation;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    conversation = await getConversation(conversationId);
    if (conversation.messages.length === 2) {
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  assert.equal(conversation.messages.length, 2);
  const reply = conversation.messages[1];
  assert.equal(reply.status, 'stopped');
  assert.match(reply.content, /partial/);

  // Retrying the same client message id regenerates instead of replaying.
  const retry = await sendMessage(conversationId, 'try again now', clientMessageId);
  assert.equal(retry.status, 200);
  const events = await readSseEvents(retry);
  const result = events.find((entry) => entry.event === 'result');
  assert.equal(result.data.grounded, true);

  const finalConversation = await getConversation(conversationId);
  assert.equal(finalConversation.messages.length, 2);
  assert.equal(finalConversation.messages[1].status, 'complete');
});

test('maps upstream rate limiting to 429 with retry-after', async () => {
  const conversationId = await createConversation();
  const response = await sendMessage(
    conversationId,
    'TRIGGER_RATE_LIMIT now',
    crypto.randomUUID(),
  );
  assert.equal(response.status, 429);
  assert.equal(response.headers.get('retry-after'), '7');
});

test('maps upstream auth failure to actionable 503 without leaking internals', async () => {
  const conversationId = await createConversation();
  const response = await sendMessage(
    conversationId,
    'TRIGGER_AUTH now',
    crypto.randomUUID(),
  );
  assert.equal(response.status, 503);
  const payload = await response.json();
  assert.match(payload.detail, /not authorized/);
  assert.ok(!JSON.stringify(payload).includes(TEST_TOKEN));
});

test('forwards upstream stream errors without persisting a reply', async () => {
  const conversationId = await createConversation();
  const clientMessageId = crypto.randomUUID();
  const response = await sendMessage(
    conversationId,
    'TRIGGER_ERROR_EVENT now',
    clientMessageId,
  );
  assert.equal(response.status, 200);
  const events = await readSseEvents(response);
  assert.ok(events.some((entry) => entry.event === 'error'));
  assert.ok(!events.some((entry) => entry.event === 'result'));

  const conversation = await getConversation(conversationId);
  assert.equal(conversation.messages.length, 1);

  // A retry after the failure succeeds with the same idempotency key.
  const retry = await sendMessage(conversationId, 'recovered question', clientMessageId);
  assert.equal(retry.status, 200);
  const retryEvents = await readSseEvents(retry);
  assert.ok(retryEvents.some((entry) => entry.event === 'result'));
  const finalConversation = await getConversation(conversationId);
  assert.equal(finalConversation.messages.length, 2);
});

test('reports the outage clearly when the knowledge service is down', async () => {
  await new Promise((resolve) => stubServer.close(resolve));

  const health = await fetch(gatewayUrl('/api/health'));
  const healthPayload = await health.json();
  assert.equal(healthPayload.status, 'degraded');
  assert.equal(healthPayload.knowledge_service.reachable, false);

  const conversationId = await createConversation();
  const response = await sendMessage(conversationId, 'anyone there?', crypto.randomUUID());
  assert.equal(response.status, 502);
  const payload = await response.json();
  assert.match(payload.detail, /unreachable/);

  // Conversation persistence still works while the upstream is down, and the
  // user message is kept for a later retry.
  const conversation = await getConversation(conversationId);
  assert.equal(conversation.messages.length, 1);

  stubServer = http.createServer(stubHandler);
  await listen(stubServer, stubPort);
});

test('conversation persistence survives a gateway process restart (state on disk)', async () => {
  const conversationId = await createConversation();
  const send = await sendMessage(conversationId, 'durable?', crypto.randomUUID());
  await readSseEvents(send);

  // Read the stored conversation straight from the durable state directory,
  // the same files a restarted gateway serves.
  const stored = JSON.parse(
    fs.readFileSync(
      path.join(stateDir, 'conversations', `${conversationId}.json`),
      'utf8',
    ),
  );
  assert.equal(stored.messages.length, 2);
  assert.equal(stored.messages[1].status, 'complete');
});
