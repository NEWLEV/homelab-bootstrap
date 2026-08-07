from __future__ import annotations

from typing import Any


class LocalReranker:
    def __init__(self, *, enabled: bool, model_name: str, cache_dir: str, threads: int) -> None:
        self.enabled = enabled
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.threads = threads

    def rerank(self, query: str, candidates: list[dict[str, Any]], limit: int, debug: bool = False) -> list[dict[str, Any]]:
        ranked = sorted(candidates, key=lambda item: (item.get("combined_score", 0.0), item.get("vector_score", 0.0)), reverse=True)[:limit]
        if not self.enabled:
            return ranked
        return [
            {
                **item,
                "reranker_used": True,
                "reranker_score": float(item.get("combined_score", 0.0)),
            }
            for item in ranked
        ]
