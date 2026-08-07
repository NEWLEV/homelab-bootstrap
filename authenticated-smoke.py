import json
import urllib.request
from pathlib import Path


token = Path(
    "/srv/data/services/local-rag/secrets/api-token"
).read_text(encoding="utf-8").strip()
headers = {"Authorization": f"Bearer {token}"}

metrics_request = urllib.request.Request(
    "http://127.0.0.1:8090/metrics",
    headers=headers,
)
with urllib.request.urlopen(metrics_request, timeout=30) as response:
    metrics = json.load(response)
    print(
        json.dumps(
            {
                "metrics_status": response.status,
                "counter_names": sorted(metrics["counters"]),
            }
        )
    )

search_headers = {
    **headers,
    "Content-Type": "application/json",
}
search_request = urllib.request.Request(
    "http://127.0.0.1:8090/search",
    data=json.dumps({"query": "OLLAMA_URL", "limit": 1}).encode(),
    headers=search_headers,
    method="POST",
)
with urllib.request.urlopen(search_request, timeout=180) as response:
    result = json.load(response)
    print(
        json.dumps(
            {
                "search_status": response.status,
                "count": result["count"],
                "first_path": result["results"][0]["path"],
            }
        )
    )
