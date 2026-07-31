# Local RAG Resource Controls

Local RAG bounds expensive API work so concurrent clients cannot exhaust the
Raspberry Pi. Production applies controls to:

- `POST /search`
- `POST /ask`
- `POST /ask/stream`
- `POST /index`

Health, metrics, status, integrity, and statistics endpoints remain outside
the request-rate and concurrency gates. Authentication still protects every
route except `GET /health`.

## Production defaults

The Compose stack configures:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Sustained requests per client IP |
| `RATE_LIMIT_BURST` | `10` | Immediate token-bucket capacity |
| `MAX_CONCURRENT_REQUESTS` | `2` | Simultaneous controlled requests |
| `MAX_REQUEST_BODY_BYTES` | `65536` | Maximum controlled request body |

The application defaults each control to disabled when its limit is zero,
which preserves isolated test and development behavior. Production Compose
sets explicit nonzero values.

Rate-limited requests return `429` with `Retry-After`. Requests rejected
because both resource slots are occupied return `503` with `Retry-After: 1`.
Oversized bodies return `413`. Rejections are counted in `/metrics`.

The rate limiter keys directly from the connected client address and does not
trust forwarded-IP headers. If a trusted reverse proxy is added later, its
address policy must be designed explicitly before forwarded headers are used.

## Operational notes

Streaming requests hold a concurrency slot until the response stream closes,
including client disconnects. Limits are process-local; keep the API at one
worker unless a shared limiter is deliberately introduced.

Tune one setting at a time and verify `/health`, authenticated search, answer
streaming, indexing, and the rejection counters. Invalid negative or
non-integer settings fail closed during application startup.
