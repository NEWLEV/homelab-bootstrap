import json
import urllib.request

queries = (
    "When do backups run?",
    "How is the Local RAG API exposed?",
    "Which port publishes local-rag-api?",
    "How are encrypted backups configured?",
    "What color is the moon base cafeteria?",
)

for query in queries:
    payload = json.dumps({"query": query, "limit": 5, "debug": True}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:8090/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.load(response)
    print(f"QUERY: {query}")
    for result in body["results"][:3]:
        print(json.dumps({
            "path": result["path"],
            "combined": result.get("combined_score"),
            "tokens": result.get("matching_tokens"),
            "reranker": result.get("reranker_score"),
            "used": result.get("reranker_used"),
        }, sort_keys=True))
