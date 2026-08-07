import json
import urllib.request
from pathlib import Path


token = Path(
    "/srv/data/services/local-rag/secrets/api-token"
).read_text(encoding="utf-8").strip()
request = urllib.request.Request(
    "http://127.0.0.1:8090/index/integrity",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(request, timeout=30) as response:
    print(json.dumps(json.load(response), sort_keys=True))
