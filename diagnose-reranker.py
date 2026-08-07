import json
import urllib.request

for query in ("local-rag.yml", "local-rag-api"):
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
    for result in body["results"]:
        print(json.dumps({
            "path": result["path"],
            "rank": result["rank"],
            "hybrid_rank": result.get("hybrid_rank"),
            "combined_score": result.get("combined_score"),
            "reranker_score": result.get("reranker_score"),
            "matching_tokens": result.get("matching_tokens"),
            "reranker_used": result.get("reranker_used"),
            "reranker_error": result.get("reranker_error"),
        }, sort_keys=True))
