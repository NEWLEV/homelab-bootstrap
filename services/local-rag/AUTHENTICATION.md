# Local RAG API Authentication

Local RAG uses a single Bearer token for every API route except
`GET /health`. The health endpoint remains public so Docker can determine
whether the service is ready without learning the credential.

Production reads the token from this external file:

```text
/srv/data/services/local-rag/secrets/api-token
```

The file is not stored in Git. Create it idempotently from the repository
root before starting the Compose stack:

```sh
scripts/local-rag-token
docker compose -f compose/ai/local-rag.yml up -d api
```

The script preserves an existing non-empty token. It creates the containing
directory with mode `0700` and the token with mode `0604`. The file needs its
other-read bit because Docker Compose bind-mounts file-backed secrets without
remapping ownership to the image's unprivileged UID; host access is still
restricted by the non-traversable `0700` parent directory.

## Calling the API

Read the token without printing it, send it in the Authorization header, and
remove it from the shell variable afterward:

```sh
token="$(< /srv/data/services/local-rag/secrets/api-token)"
curl -H "Authorization: Bearer ${token}" \
  http://127.0.0.1:8090/metrics
unset token
```

Requests with a missing, malformed, or incorrect token receive `401` and a
`WWW-Authenticate: Bearer` response header. Documentation and the OpenAPI
schema are protected along with operational and AI endpoints.

## Configuration

The application accepts exactly one token source:

- `API_AUTH_TOKEN_FILE` — preferred for production
- `API_AUTH_TOKEN` — intended for controlled development or tests

If a configured file is missing or unreadable, both sources are present, or
the token is empty, shorter than 32 characters, or contains whitespace, the
application fails closed during startup.

The Compose host token path can be overridden when necessary:

```sh
LOCAL_RAG_API_TOKEN_FILE=/secure/path/api-token \
  docker compose -f compose/ai/local-rag.yml up -d api
```

## Rotation

Rotate the token during a maintenance window by atomically replacing the
external file with a new 32-byte random value, restoring mode `0604`, and
force-recreating the API container. Existing clients stop authenticating as
soon as the recreated service starts. Never print, log, or commit either
token.
