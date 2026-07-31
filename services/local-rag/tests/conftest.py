"""Shared test-environment configuration.

The Compose service uses production-like settings. Tests must establish
their own deterministic defaults before test modules import app.main.
"""

import os


# Authentication is disabled by default in ordinary API tests.
# Authentication-specific tests enable it explicitly with monkeypatch.
os.environ.pop("API_AUTH_TOKEN", None)
os.environ.pop("API_AUTH_TOKEN_FILE", None)

# Keep health endpoint expectations and unit tests independent of the
# production Compose configuration.
os.environ["RERANKER_ENABLED"] = "false"
os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "0"
os.environ["RATE_LIMIT_BURST"] = "10"
os.environ["MAX_CONCURRENT_REQUESTS"] = "0"
os.environ["MAX_REQUEST_BODY_BYTES"] = "0"
