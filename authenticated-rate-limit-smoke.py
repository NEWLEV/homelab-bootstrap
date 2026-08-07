import json
import urllib.error
import urllib.request
from pathlib import Path


token = Path(
    "/srv/data/services/local-rag/secrets/api-token"
).read_text(encoding="utf-8").strip()
statuses = []

for _ in range(11):
    request = urllib.request.Request(
        "http://127.0.0.1:8090/search",
        data=b'{"query":"   "}',
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            statuses.append(response.status)
    except urllib.error.HTTPError as exc:
        statuses.append(exc.code)

metrics_request = urllib.request.Request(
    "http://127.0.0.1:8090/metrics",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(metrics_request, timeout=30) as response:
    counters = json.load(response)["counters"]

print(json.dumps({
    "statuses": statuses,
    "rate_limited_requests": counters["rate_limited_requests"],
}, sort_keys=True))
