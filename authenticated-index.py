import json
import urllib.request
from pathlib import Path


token = Path(
    "/srv/data/services/local-rag/secrets/api-token"
).read_text(encoding="utf-8").strip()
request = urllib.request.Request(
    "http://127.0.0.1:8090/index",
    headers={"Authorization": f"Bearer {token}"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=300) as response:
    result = json.load(response)
    print(
        json.dumps(
            {
                "status": result["status"],
                "files": result["files"],
                "skipped_files": result["skipped_files"],
                "added_chunks": result["added_chunks"],
                "updated_chunks": result["updated_chunks"],
                "skipped_chunks": result["skipped_chunks"],
                "removed_chunks": result["removed_chunks"],
                "total_chunks": result["total_chunks"],
            }
        )
    )
