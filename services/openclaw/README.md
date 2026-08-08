# OpenClaw Service — Aisha Chat Gateway

This directory implements the OpenClaw runtime boundary and the Aisha chat
gateway that runs inside it.

OpenClaw is the internal gateway service for the local assistant runtime.
Aisha is the user-facing assistant identity; every user-visible surface of
this service is branded Aisha, while OpenClaw remains the internal service
and container name.

## What the gateway does

- Serves the Aisha chat interface (`ui/`) as static, self-contained assets.
- Exposes a conversation API under `/aisha/api/`:
  - `GET /aisha/api/health` — sanitized aggregate health of the gateway and
    the Local RAG knowledge service. No paths or secrets are included.
  - `GET|POST /aisha/api/conversations` — list and create conversations.
  - `GET|DELETE /aisha/api/conversations/{id}` — fetch and delete one.
  - `POST /aisha/api/conversations/{id}/messages` — send a question. The
    gateway forwards it to the Local RAG `/ask/stream` endpoint and relays
    the SSE `token`, `result`, and `error` events to the browser.
- Holds the Local RAG bearer token server-side. The token is mounted as the
  `local_rag_api_token` Compose secret and never reaches the browser.
- Persists conversations as JSON under `/state/conversations/`
  (host path `/srv/data/services/openclaw/conversations`, covered by the
  backup manifest).
- Enforces idempotent message submission via a client-supplied
  `client_message_id` UUID: retries replay the stored answer instead of
  regenerating, and concurrent duplicates are rejected.
- Aborts the upstream generation when the browser cancels, and stores a
  clearly labeled `stopped` partial answer.

## Exposure and trust boundary

Two access paths are supported, matching how the dashboard itself is
reached:

1. **Through Traefik** — `https://aisha.tail4553c9.ts.net/aisha/`, same
   origin as the dashboard host.
2. **Direct dashboard access** — when Homepage is used at
   `http://aisha:8000` or `http://100.106.201.14:8000`, the launcher falls
   back to the gateway's published port `18790` on the same host. The
   dashboard origin must be listed in `OPENCLAW_EMBED_ORIGINS`; that
   allowlist drives both the CSP `frame-ancestors` directive and CORS,
   which is enabled for `GET /api/health` only — all conversation traffic
   stays same-origin inside the embedded frame.

The legacy `/health` and `/ready` endpoints are not served under the
`/aisha` prefix. Note that direct access is plain HTTP; response copy
buttons are hidden there because the browser clipboard API requires a
secure context.

This appliance has no user-account or session system — the Homepage
dashboard it sits beside has none either. Authorization for the chat is
therefore the same boundary that protects the rest of the dashboard: the
Tailscale tailnet plus Traefik TLS. Conversations are scoped to the
appliance, not to individual user accounts, and the API surface reflects
that honestly rather than implying per-user isolation that does not exist.

If per-user isolation is required later, the correct place to add it is a
Traefik forward-auth middleware in front of both the dashboard and this
route, with the authenticated identity threaded into the conversation
storage key. That is deliberately out of scope here, because inventing a
local user store would duplicate infrastructure the appliance does not have.

Answers are grounded in the indexed repository only. The gateway sends the
user's question and the bounded recent conversation history upstream, and
nothing else — no dashboard state, service inventory, or host telemetry is
silently attached.

## Runtime contract

- `start.sh` validates the secrets file, prepares writable directories, and
  launches the gateway. A missing Local RAG token is a warning, not a fatal
  error: the chat then truthfully reports itself unavailable.
- `server.js` implements the gateway described above.
- `healthcheck.sh` verifies the service is alive and the secret boundary is
  present.
- `Dockerfile` builds a small image with the server and the chat UI.
- Compose mounts durable state under `/srv/data/services/openclaw`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCLAW_LOCAL_RAG_URL` | `http://local-rag-api:8080` | Knowledge service endpoint |
| `OPENCLAW_LOCAL_RAG_TOKEN_FILE` | `/run/secrets/local_rag_api_token` | Bearer token file |
| `OPENCLAW_GATEWAY_BIND` | `127.0.0.1` (compose sets `0.0.0.0`) | Listen address |
| `OPENCLAW_GATEWAY_PORT` | `18790` | Listen port |
| `OPENCLAW_STATE_DIR` | `/state` | Durable state root |
| `OPENCLAW_UI_DIR` | `/usr/local/share/openclaw-ui` | Chat UI assets |

The token file is provisioned on the host with `scripts/local-rag-token`
(the same file the Local RAG API reads).

## Dashboard launcher

The Homepage dashboard loads a floating "Chat with Aisha" launcher from
repository-managed assets in `configs/homepage/`. Install them with
`scripts/install-homepage-aisha-launcher`.

## Deployment

From the repository root on Aisha:

```bash
scripts/install-openclaw-runtime
docker compose -f compose/ai/openclaw.yml config --quiet
docker compose -f compose/ai/openclaw.yml up -d --build
docker compose -f compose/ai/openclaw.yml ps
curl --fail http://127.0.0.1:18790/aisha/api/health
```

The health response can report `ready: false` when Local RAG is unavailable or
its token has not been provisioned. A connection refusal means the OpenClaw
container is not running or port `18790` is not published.

## Validation

```bash
./tests/aisha-chat.sh
node --test services/openclaw/test/gateway.test.js
docker compose -f compose/ai/openclaw.yml config --quiet
```
