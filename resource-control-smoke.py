import json
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8090"
TOKEN_FILE = Path("/srv/data/services/local-rag/secrets/api-token")


def request(
    path: str,
    *,
    body: bytes | None = None,
    authenticated: bool = False,
) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if authenticated:
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        headers["Authorization"] = f"Bearer {token}"
    api_request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(api_request, timeout=180) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


health_status, health = request("/health")
unauthenticated_statuses = [
    request("/search", body=b'{"query":"OLLAMA_URL"}')[0]
    for _ in range(12)
]
search_status, search = request(
    "/search",
    body=b'{"query":"OLLAMA_URL","limit":1}',
    authenticated=True,
)
oversized_status, _ = request(
    "/search",
    body=json.dumps({"query": "q" * 70000}).encode("utf-8"),
    authenticated=True,
)
metrics_status, service_metrics = request(
    "/metrics",
    authenticated=True,
)

print(json.dumps({
    "health_status": health_status,
    "version": health.get("version"),
    "rate_limiting_enabled": health.get("rate_limiting_enabled"),
    "rate_limit_requests_per_minute": health.get(
        "rate_limit_requests_per_minute"
    ),
    "max_concurrent_requests": health.get("max_concurrent_requests"),
    "max_request_body_bytes": health.get("max_request_body_bytes"),
    "unauthenticated_statuses": sorted(set(unauthenticated_statuses)),
    "authenticated_search_status": search_status,
    "authenticated_search_first_path": (
        search.get("results", [{}])[0].get("path")
    ),
    "oversized_status": oversized_status,
    "metrics_status": metrics_status,
    "oversized_request_count": service_metrics.get(
        "counters", {}
    ).get("oversized_requests"),
}, sort_keys=True))
